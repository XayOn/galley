"""Views."""
import json
import base64
from pathlib import Path
from fnmatch import fnmatch
from io import BytesIO
from zipfile import ZipFile
from aiohttp.web import View, json_response, HTTPUnauthorized, HTTPNotFound
from .models import Book, Page, PageRevision, Vote

RES = {True: 1, False: -1}


async def get_user(request, body: dict):
    """Return user with ip."""
    return request.remote + body.get('user', '')


class BookView(View):
    """Book."""

    async def get(self, book_id: int = 0):
        """Return book or all books, if id is 0, returns all."""
        if book_id != 0:
            book = await Book.filter(id=book_id).values('id', 'pages__number')
            return json_response(book)
        return json_response(await Book.all())

    async def post(self):
        """Create book from zipfile."""
        file = BytesIO(await self.request.read())
        file = ZipFile(file)
        creator = await get_user(self.request, {})
        book = await Book.create(creator=creator)

        numbers = []
        files = [a for a in file.namelist() if fnmatch(a, '*/*.txt')]
        for text_file in files:
            number = Path(text_file).stem.replace('page_', '')
            text = file.read(text_file)
            image_file = text_file.replace('text', 'jpg')
            image = file.read(image_file)
            numbers.append(number)
            await Page.create(book_id=book.id,
                              text=text.decode(),
                              number=int(number),
                              image=base64.b64encode(image))
        return json_response({'book_id': book.id, 'pages': numbers})


class BookRevision(View):
    """Handle revisions."""

    async def get(self, book_id: int, page: int, revision: int):
        """Return text."""
        page = await Page.filter(book=book_id, number=page).first()
        revision = await PageRevision.filter(page=page.id,
                                             id=revision).first()
        return json_response(
            dict(text=revision.text, score=await revision.score()))

    async def put(self, book_id: int, page: int, revision: int,
                  body: dict):
        """Vote revision."""
        page = await Page.filter(book=book_id, number=page).first()
        revision = await PageRevision.filter(page=page, id=revision).first()

        user = await get_user(self.request, body)
        votes = [vote async for vote in revision.votes]

        if any([vote.user == user for vote in votes]):
            raise HTTPUnauthorized(body=json.dumps({'status': 'already_voted'}))

        await Vote().create(revision=revision,
                            user=user,
                            result=RES.get(body['approved']))

        await revision.save()
        return json_response({'result': 'ok'})


class BookPage(View):
    """Handle revisions."""

    async def get(self, book_id: int, page=None):
        """Return text."""
        page = await Page.filter(book_id=int(book_id), number=int(page)).first()
        if not page:
            raise HTTPNotFound()
        return json_response({
            'id': page.id,
            'number': page.number,
            'text': page.text,
            'revisions': {r.id: (await r.score)
                          async for r in page.revisions}
        })

    async def post(self, book_id, page: int, body: dict):
        """Create a page revision."""
        user = await get_user(self.request, body)
        page = await Page.filter(book=book_id, number=page).first()
        revision = await PageRevision.create(page=page,
                                             owner=user,
                                             text=body.get('text'))
        return json_response({'revision_id': revision.id})
