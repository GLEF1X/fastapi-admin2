from operator import eq
from typing import no_type_check, Tuple, Optional, Any, Iterable, TypeVar, Union, List

from sqlalchemy import inspect, ForeignKey, Column, tuple_, and_, or_
from sqlalchemy.ext.associationproxy import ASSOCIATION_PROXY
from sqlalchemy.orm import RelationshipProperty, MapperProperty
from sqlalchemy.sql.elements import BooleanClauseList


def parse_like_term(term: str) -> str:
    if term.startswith('^'):
        stmt = '%s%%' % term[1:]
    elif term.startswith('='):
        stmt = term[1:]
    else:
        stmt = '%%%s%%' % term

    return stmt


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


def _resolve_prop(prop: MapperProperty) -> MapperProperty:
    """
        Resolve proxied property
        :param prop:
            Property to resolve
    """
    # Try to see if it is proxied property
    if hasattr(prop, '_proxied_property'):
        return prop._proxied_property

    return prop


def _find_relation_for_foreign_key(relationships: Iterable[RelationshipProperty],
                                   local_foreign_key_column: Any) -> Optional[RelationshipProperty]:
    for relationship in relationships:
        for pair in relationship.synchronize_pairs:
            for c in pair:
                if c == local_foreign_key_column:
                    return relationship
    return None


_S = TypeVar("_S", bound=Any)


def include_where_condition_by_pk(statement: _S, model: Any, ids: Union[List[Any], Any],
                                  dialect_name: str) -> _S:
    """
    Return a query object filtered by primary key values passed in `ids` argument.
    Unfortunately, it is not possible to use `in_` filter if model has more than one
    primary key.
    """
    if has_multiple_pks(model):
        model_pk = [getattr(model, name) for name in get_primary_key(model)]
    else:
        model_pk = getattr(model, get_primary_key(model))

    if isinstance(ids, str):
        if not has_multiple_pks(model):
            statement = statement.where(model_pk == ids)
        else:
            statement = statement.where(
                or_(
                    *[pk == ids for pk in model_pk]
                )
            )
    else:
        if has_multiple_pks(model):
            if dialect_name != "sqlite":
                statement = statement.where(tuple_(*model_pk).in_(ids))
            else:
                statement = statement.where(tuple_operator_in(model_pk, ids))
        else:
            ids = map(model_pk.type.python_type, ids)  # type: ignore
            statement = statement.where(model_pk.in_(ids))  # type: ignore

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


def is_relationship(attr: Any) -> bool:
    return hasattr(attr, 'property') and hasattr(attr.property, 'direction')


def is_association_proxy(attr: Any) -> bool:
    if hasattr(attr, 'parent'):
        attr = attr.parent
    return hasattr(attr, 'extension_type') and attr.extension_type == ASSOCIATION_PROXY
