from operator import eq
from typing import Tuple, Optional, Any, no_type_check, List, Union, TypeVar, Iterable

from sqlalchemy import ForeignKey, inspect, and_, or_, Column, tuple_
from sqlalchemy.orm import RelationshipProperty
from sqlalchemy.sql import Select, Insert
from sqlalchemy.sql.dml import UpdateBase
from sqlalchemy.sql.elements import BooleanClauseList


@no_type_check
def get_primary_key(model):
    """
        Return primary key name from a model. If the primary key consists of multiple columns,
        return the corresponding tuple
        :param model:
            Model class
    """
    mapper = model._sa_class_manager.mapper
    pks = [mapper.get_property_by_column(c).key for c in mapper.primary_key]
    if len(pks) == 1:
        return pks[0]
    elif len(pks) > 1:
        return tuple(pks)
    else:
        return None


@no_type_check
def get_related_querier_from_model_by_foreign_key(column):
    """
    Return querier for related model

    :param column: local column with foreign key
    :return:
    """
    model = inspect(column).class_
    column_foreign_key: ForeignKey = next(iter(column.foreign_keys))
    relationships: Tuple[RelationshipProperty, ...] = tuple(inspect(model).relationships)
    relation_for_foreign_key = _find_relation_for_foreign_key(relationships, column)
    querier: Optional[Any] = None
    if relation_for_foreign_key is not None:
        querier_table = relation_for_foreign_key.target
    else:
        querier_table = column_foreign_key.constraint.referred_table

    for mapper in model._sa_class_manager.registry.mappers:
        if mapper.persist_selectable == querier_table:
            querier = mapper.class_
    if querier is None:
        raise Exception("Unable to find table to which mapped foreign key/relationship")
    return querier


def _find_relation_for_foreign_key(relationships: Iterable[RelationshipProperty],
                                   local_foreign_key_column: Any) -> Optional[RelationshipProperty]:
    for relationship in relationships:
        for pair in relationship.synchronize_pairs:
            for c in pair:
                if c == local_foreign_key_column:
                    return relationship
    return None


_S = TypeVar("_S", bound=Union[UpdateBase, Insert, Select])


def include_where_condition_by_pk(statement: _S, model: Any, ids: List[Any]) -> _S:
    """
    Return a query object filtered by primary key values passed in `ids` argument.
    Unfortunately, it is not possible to use `in_` filter if model has more than one
    primary key.
    """
    if has_multiple_pks(model):
        model_pk: List[Column] = [getattr(model, name) for name in get_primary_key(model)]
        statement = statement.where(tuple_(*model_pk).in_(ids))
    else:
        model_pk: Column = getattr(model, get_primary_key(model))
        ids = map(model_pk.type.python_type, ids)
        statement = statement.where(model_pk.in_(ids))

    return statement


def has_multiple_pks(model: Any) -> bool:
    """
    Return True, if the model has more than one primary key
    """
    if not hasattr(model, '_sa_class_manager'):
        raise TypeError('model must be a sqlalchemy mapped model')

    return len(model._sa_class_manager.mapper.primary_key) > 1


def tuple_operator_in(model_pk: List[Column], ids: List[Any]) -> Optional[BooleanClauseList]:
    """The tuple_ Operator only works on certain engines like MySQL or Postgresql. It does not work with sqlite.
    The function returns an or_ - operator, that contains and_ - operators for every single tuple in ids.
    Example::
      model_pk =  [ColumnA, ColumnB]
      ids = ((1,2), (1,3))
      tuple_operator(model_pk, ids) -> or_( and_( ColumnA == 1, ColumnB == 2), and_( ColumnA == 1, ColumnB == 3) )
    The returning operator can be used within a filter(), as it is just an or_ operator
    """
    and_conditions = []
    for id in ids:
        conditions = []
        for i in range(len(model_pk)):
            conditions.append(eq(model_pk[i], id[i]))
        and_conditions.append(and_(*conditions))
    if len(and_conditions) >= 1:
        return or_(*and_conditions)
    else:
        return None
