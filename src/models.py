from google.appengine.api import users
from google.appengine.ext import db

class GeneralSiteProperties(db.Model):
    tag_line = db.StringProperty(required=True)

    @classmethod
    def get_properties(cls):
        return cls.all()[0]

class Image(db.Model) :
    name = db.StringProperty(required=True)
    picture = db.BlobProperty(required=True)
    title = db.StringProperty(required=True)
    alt = db.StringProperty(required=True)

def getImage(name):
    result = db.GqlQuery("SELECT * FROM Image WHERE name = :1 LIMIT 1",
                      name).fetch(1)
    if (len(result) > 0):
          return result[0]
    else:
          return None

class Member(db.Model):
    user_id = db.StringProperty(required=True)
    email = db.StringProperty(default='')
    handle = db.StringProperty(required=True)
    bio = db.TextProperty(default='')
    real_name = db.StringProperty(default='')
    score = db.IntegerProperty(default=0)

    @classmethod
    def get_current_member(cls):
        user = users.get_current_user()
        if not user:
            return
        user_id = user.user_id()
        member = cls.gql('WHERE user_id = :1', user_id).get()
        if not member:
            member = cls(user_id=user_id, handle=user_id)
            member.put()
        return member


class NewsArticleNew(db.Model):

    title = db.TextProperty(required=True)
    author = db.ReferenceProperty(Member, required=True)
    date = db.DateProperty(required=True)
    body = db.TextProperty(required=True)
    picture = db.ReferenceProperty(Image)

class TalkNew(db.Model):

    title = db.TextProperty(required=True)
    author = db.ReferenceProperty(Member, required=True, collection_name='talks')
    date = db.DateProperty(required=True)
    video = db.LinkProperty()
    body = db.TextProperty()

class Hack(db.Model):

    title = db.TextProperty(required=True)
    date = db.DateProperty(required=True)
    body = db.TextProperty(required=True)
    picture = db.ReferenceProperty(Image)