"""Models."""

from tortoise.models import Model
from tortoise import fields


class Book(Model):
    """Book."""

    id = fields.IntField(pk=True)
    creator = fields.TextField()
    pages : fields.ReverseRelation["Page"]


class Page(Model):
    """Page."""

    id = fields.IntField(pk=True)
    number = fields.IntField()
    book: fields.ForeignKeyRelation[Book] = fields.ForeignKeyField(
        "models.Book", related_name="pages")
    text = fields.TextField()
    image = fields.TextField()
    revisions : fields.ReverseRelation["PageRevision"]


class PageRevision(Model):
    """Page revision."""

    id = fields.IntField(pk=True)
    page: fields.ForeignKeyRelation[Page] = fields.ForeignKeyField(
        "models.Page", related_name="revisions")
    owner = fields.TextField()
    text = fields.TextField()
    votes : fields.ReverseRelation["Vote"]

    async def score(self) -> int:
        """Return total score on votes."""
        await self.fetch_related("votes")
        return sum([a.result for a in self.votes])


class Vote(Model):
    """Vote for a revision."""

    id = fields.IntField(pk=True)
    revision: fields.ForeignKeyRelation[PageRevision] = fields.ForeignKeyField(
        "models.PageRevision", related_name="votes")
    user = fields.TextField()
    result = fields.IntField()
