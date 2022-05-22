"""Views."""
import json
import base64
from pathlib import Path
from fnmatch import fnmatch
from io import BytesIO
from zipfile import ZipFile
from aiohttp.web import View, json_response, HTTPUnauthorized
from .models import Book, Page, PageRevision, Vote

RES = {True: 1, False: -1}


async def get_user(request, body: dict):
    """Return user with ip."""
    return request.remote + body.get('user', '')


async def create_book(request):
    """Create book from zipfile."""
    file = BytesIO(await request.read())
    file = ZipFile(file)
    book = await Book.create()

    numbers = []
    for json_file in [a for a in file.namelist() if fnmatch(a, '*/*.json')]:
        number = Path(json_file).stem.replace('page_', '')
        text = json.loads(file.read(json_file)).get('text')
        image_file = json_file.replace('json', 'jpg')
        image = file.read(image_file)
        numbers.append(number)
        await Page.create(book_id=book.id,
                          text=text,
                          number=number,
                          image=base64.b64encode(image))
    return json_response({'book_id': book.id, 'pages': numbers})


class BookRevision(View):
    """Handle revisions."""

    async def get(self, book_id: int, page_id: int, revision_id: int):
        """Return text."""
        page = await Page.find(book=book_id, page_number=page_id).first()
        revision = await PageRevision.filter(book=book_id,
                                             page=page.id,
                                             number=revision_id).first()
        return json_response(
            dict(text=revision.text,
                 score=sum([a.result async for a in revision.votes])))

    async def put(self, book_id: int, page_id: int, revision_id: int,
                  body: dict):
        """Vote revision."""
        page = await Page.find(book=book_id, page_number=page_id).first()
        revision = await PageRevision.filter(
            book=book_id, page=page.id, revision_number=revision_id).first()

        user = await get_user(self.request, body.get('user'))
        votes = [vote async for vote in revision.votes]

        if any([vote.user == user for vote in votes]):
            raise HTTPUnauthorized('already_voted')

        await Vote().create(revision=revision,
                            user=user,
                            result=RES.get(body['approved']))

        await revision.save()
        return json_response({'result': 'ok'})


class BookPage(View):
    """Handle revisions."""

    async def get(self, book_id: int , page_id=None):
        """Return text."""
        page = await Page.filter(book=book_id, page_number=page_id).first()
        return {
            'id': page.id,
            'number': page.page_number,
            'text': page.text,
            'revisions': {r.id: (await r.score)
                          async for r in page.revisions}
        }

    async def post(self, book_id, page_id: int, body: dict):
        """Create a page revision."""
        user = await get_user(self.request, body)
        page = await Page.filter(book=book_id, page=page_id).first()
        revision = await PageRevision.create(page=page.id,
                                             owner=user,
                                             text=body.get('text'))
        return json_response({'revision_id': revision.id})
