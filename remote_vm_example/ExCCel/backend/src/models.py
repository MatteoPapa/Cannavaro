import dataclasses
from typing import List

from sqlalchemy import ForeignKey, Text, Integer, Column, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import db, Base
from storage import Cell

worksheet_guest = Table(
    'worksheet_guest', Base.metadata,
    Column('worksheet_id', Text, ForeignKey('worksheet.public_id')),
    Column('guest_id', Integer, ForeignKey('user.id'))
)


class User(db.Model):
    __table_name__ = 'user'

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str]
    worksheets: Mapped[List['Worksheet']] = relationship('Worksheet', back_populates='owner')
    guest_worksheets: Mapped[List['Worksheet']] = relationship('Worksheet', secondary=worksheet_guest,
                                                               back_populates='guests')
    comments: Mapped[List['Comment']] = relationship('Comment', back_populates='owner')


class Worksheet(db.Model):
    __table_name__ = 'worksheet'

    public_id: Mapped[str] = mapped_column(primary_key=True)
    private_id: Mapped[str]
    title: Mapped[str]
    sharable: Mapped[bool]
    owner_id: Mapped[int] = mapped_column(ForeignKey('user.id'))
    owner: Mapped['User'] = relationship('User', back_populates='worksheets')
    guests: Mapped[List['User']] = relationship('User', secondary=worksheet_guest, back_populates='guest_worksheets')
    comments: Mapped[List['Comment']] = relationship('Comment', back_populates='worksheet')

    def as_light_dict(self) -> dict:
        return {
            'id': self.public_id,
            'title': self.title,
            'sharable': self.sharable,
            'owner': {
                'id': self.owner.id,
                'username': self.owner.username
            }
        }

    def as_dict(self, cells: list[Cell]) -> dict:
        return {
            'id': self.public_id,
            'title': self.title,
            'sharable': self.sharable,
            'owner': {
                'id': self.owner.id,
                'username': self.owner.username
            },
            'guests': [{'id': g.id, 'username': g.username} for g in self.guests],
            'cells': [c.as_dict() for c in cells],
            'comments': [c.as_dict() for c in self.comments]
        }


class Comment(db.Model):
    __table_name__ = 'comment'

    id: Mapped[int] = mapped_column(primary_key=True)
    cell_x: Mapped[int]
    cell_y: Mapped[int]
    created_at: Mapped[int]
    content: Mapped[str]
    worksheet_id: Mapped[str] = mapped_column(ForeignKey('worksheet.public_id'))
    worksheet: Mapped['Worksheet'] = relationship('Worksheet', back_populates='comments')
    owner_id: Mapped[int] = mapped_column(ForeignKey('user.id'))
    owner: Mapped['User'] = relationship('User', back_populates='comments')

    def as_dict(self) -> dict:
        return {
            'id': self.id,
            'x': self.cell_x,
            'y': self.cell_y,
            'created': self.created_at,
            'content': self.content,
            'owner': {
                'id': self.owner.id,
                'username': self.owner.username,
            }
        }
