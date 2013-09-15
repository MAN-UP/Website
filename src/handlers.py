import datetime
import os
import urllib

from google.appengine.api import users, datastore_errors
from google.appengine.api.mail import send_mail
from google.appengine.ext.webapp import RequestHandler, template
from google.appengine.ext.db import Key, BadKeyError
from google.appengine.api import images
from google.appengine.ext import db
# RequestTooLargeError can live in two different places.
try: 
    # When deployed
    from google.appengine.runtime import RequestTooLargeError
except ImportError:
    # In the development server
    from google.appengine.runtime.apiproxy_errors import RequestTooLargeError

import utils
from models import Member, NewsArticleNew, TalkNew, Hack,Image,\
                   GeneralSiteProperties, getImage

get_path = utils.path_getter(__file__)

## I have split the Handlers up into simple and non-simple, i.e the ones at the end are trivial and uninteresting

## Non-simple Handlers, in alphabetical order

class BaseHandler(RequestHandler):

    login_required = False
    title = None
    image_height=500
    image_width=500

    thing_descriptors = {
      'news' : "News Article",
      'hack' : "Hack-a-thon Entry",
      'talk' : "Talk"
    }

    def render_template(self, template_name, template_dict=None):
        try:
            tag_line = GeneralSiteProperties.get_properties().tag_line
        except:
            tag_line = 'Next meeting soon!'

        if template_dict is None:
            template_dict = {}

        user = Member.get_current_member()

        if user:
            if self.login_required:
                redirect_target = '/'
            else:
                redirect_target = self.request.path
            url_creator = users.create_logout_url
        else:
            redirect_target = '/login?url=%s' % self.request.path
            url_creator = users.create_login_url

        defaults = {
            'user': user,
            'is_admin': users.is_current_user_admin(),
            'log_url': url_creator(redirect_target),
            'tag_line': tag_line,
            'title': self.title
        }

        for key in defaults:
            if key not in template_dict:
                template_dict[key] = defaults[key]

        template_path = get_path(
            os.path.join('templates', '%s.html' % template_name)
        )
        self.response.out.write(template.render(template_path, template_dict))


class AccountHandler(BaseHandler):

    login_required = True

    title = 'Account'

    valid_letters = (
        'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    )

    banned_names = {
        u'neo': "Fat chance are you Neo. If you are, I'm not gonna get my hopes up",
    }

    def post(self):
        if len(self.request.POST) == 4 and 'handle' in self.request.POST \
                and 'real_name' in self.request.POST \
                and 'email' in self.request.POST \
                and 'bio' in self.request.POST:

            handle = self.request.POST.getall('handle')[0]
            template_dict = {}
            member = Member.get_current_member()
            other = Member.gql('WHERE handle = :1', handle).get()

            if (not handle or len(handle) > 12 or
                any(l not in self.valid_letters for l in handle)):
                template_dict['error'] = 'Pick something sensible, you moron.'

            elif other and other.user_id != member.user_id:
                template_dict['error'] = 'Sorry, already taken.'

            elif handle.lower() in self.banned_names:
                template_dict['error'] = self.banned_names[handle]

            else:
                real_name = self.request.POST.getall('real_name')[0]
                if real_name:
                    member.real_name = real_name
                email = self.request.POST.getall('email')[0]
                if email:
                    member.email = email
                bio = self.request.POST.getall('bio')[0]
                if bio:
                    member.bio = bio
                member.handle = handle
                member.save()
                template_dict['error'] = 'Profile updated'
            self.render_template('account', template_dict)

    def get(self):
        self.render_template('account')

class AdminHandler(BaseHandler):

    login_required = True
    admin_message = None

    def get(self):
        if 'tabselect' in self.request.GET:
           tabselect = self.request.get('tabselect')
        else:
           tabselect='general'

        self.render_template('admin',
            {'news_list' : NewsArticleNew.all().order('-date'),
             'talk_list' : TalkNew.all().order('-date'),
             'hack_list' : Hack.all().order('-date'),
             'image_list' : Image.all(),
             'image_height' : self.image_height,
             'image_width' : self.image_width,
             'members': Member.all(),
             'message' : self.admin_message,
             'tabselect':tabselect})

    def post(self):
        post = self.request.POST
        kind=post['kind']
        if  kind== 'taglineform':
            properties = GeneralSiteProperties.all().get()
            if properties == None:
                properties = GeneralSiteProperties(tag_line=post['tagline'])
                properties.put()
            else:
                properties.tag_line = post['tagline']
                properties.put()
        elif kind=="image_upload":
             if(self.request.get("picture")):
                 try:
                      if('resize' in post):
                          pictureImage = Image(picture=images.resize(self.request.get("picture"),int(post['height']), int(post['width'])),
                                               name="no-name",title=" ",alt=" ")
                      else:
                          pictureImage = Image(picture=self.request.get("picture"),name="no-name",title=" ",alt=" ")
                      if(post['alias']!=""):
                         replace=True
                         name=post['alias']
                         for other_image in Image.all():
                             if other_image.name == name :
                                replace=False
                                self.admin_message="You cannot use %s as an alias as it is used for another image" % name
                         if replace :
                             pictureImage.name=name
                      if(post['title']!=""):
                         pictureImage.name=post['title']
                      if(post['alt']!=""):
                         pictureImage.name=post['alt']
                      pictureImage.put()
                      self.admin_message = 'Image uploaded'
                 except RequestTooLargeError:
                      self.admin_message = 'Image not uploaded - too large'
                 except TypeError:
                      self.admin_message = 'Width and Height have to be integers'
             else:
                 self.admin_message = 'You need to actually select a picture!'
             kind='image'
        else :
             things_deleted = 0
             for entry_key in self.request.POST.getall('delete_entry'):
                try:
                    entry_key = Key(entry_key)
                except BadKeyError:
                    # Wrong syntax for a key, move on to next key.
                    continue
                if(kind=='news'):
                    thing = NewsArticleNew.get(entry_key)
                elif(kind=='talk'):
                    thing = TalkNew.get(entry_key)
                elif(kind=='hack'):
                    thing = Hack.get(entry_key)
                if thing:
                    thing.delete()
                    things_deleted += 1
                # Else, not article has this key.
             self.admin_message = '%d %s(s) deleted.' % (things_deleted,self.thing_descriptors.get(kind))

        self.render_template('admin',
            {'news_list' : NewsArticleNew.all().order('-date'),
             'talk_list' : TalkNew.all().order('-date'),
             'hack_list' : Hack.all().order('-date'),
             'image_list' : Image.all(),
             'image_height' : self.image_height,
             'image_width' : self.image_width,
             'members': Member.all(),
             'message' : self.admin_message,
             'tabselect':kind})




class EditHandler(BaseHandler):

    def get(self, key):
        edit = self.request.get('edit')
        template_dict = {'key': key, 'show_form' : True,'members': Member.all(),
                         'edit':edit,'thing' : self.thing_descriptors.get(edit),'images':Image.all().filter('name != ', "no-name") }
        if key == 'new':
            template_dict['form_data'] = {
                'author': Member.get_current_member().handle,
                'date': unicode(datetime.date.today())}
        else:
            try:
                if(edit=='news'):
                   thing = NewsArticleNew.get(Key(key))
                   form_data={'title':thing.title,'author':thing.author,'date':unicode(thing.date),'body':thing.body,'picture':thing.picture}
                elif(edit=='talk'):
                   thing = TalkNew.get(Key(key))
                   form_data={'title':thing.title,'author':thing.author,'date':unicode(thing.date),'body':thing.body,'video':thing.video}
                elif(edit=='hack'):
                   thing = Hack.get(Key(key))
                   form_data={'title':thing.title,'date':unicode(thing.date),'body':thing.body,'picture':thing.picture}
                template_dict['form_data']=form_data
            except BadKeyError:
                template_dict['message'] = \
                    'Could not find %s with key %r.' %  (self.thing_descriptors.get(edit), key)
                template_dict['show_form'] = False
        self.render_template('edit', template_dict)

    def post(self, key):
        post = self.request.POST
        edit = self.request.get('kind')
        form_data = dict((k, post.get(k, ''))
                          for k in ('title', 'author', 'date', 'body', 'picture','video'))
        template_dict = {'form_data': form_data, 'key': key, 'show_form' : True,'members': Member.all(),
                         'edit':edit,'thing' : self.thing_descriptors.get(edit),'images':Image.all().filter('name != ', "no-name")}

        try:
                this_date = utils.parse_date(form_data['date'])
        except ValueError:
                template_dict['message'] = \
                    'Date is not in the correct format (YYYY-MM-DD).'
        else:
                if key == 'new':
                    try:
                        if(edit=="news"):
                             thing = NewsArticleNew(
                                  title=post['title'],
                                  author=Member.get_by_id(int(post['author'])),
                                  date=this_date,
                                  body=post['body']
                             )
                        elif(edit=="talk"):
                             thing = TalkNew(
                                  title=post['title'],
                                  author=Member.get_by_id(int(post['author'])),
                                  date=this_date,
                                  body=post['body']
                             )
                             if('video' in post):
                                 talk.video = post['video']
                        elif(edit=="hack"):
                             thing = Hack(
                                  title=post['title'],
                                  date=this_date,
                                  body=post['body']
                             )
                        if(edit=="news" or edit=="hack"):
                             if(self.request.get("picture")):
                                  pictureImage = Image(
                                               picture=images.resize(self.request.get("picture"), self.image_height, self.image_width),
                                               name="no-name",title=" ",alt=" ")
                                  if post['picture_title'] :
                                     pictureImage.title=post['picture_title']
                                  if post['picture_alt'] :
                                     pictureImage.alt=post['picture_alt']
                                  pictureImage.put()
                                  thing.picture=pictureImage
                             elif(post['picture_alias']!="none"):
                                  thing.picture=Image.get_by_id(int(post['picture_alias']))

                        thing.put()
                        template_dict['key']=thing.key

                    except datastore_errors.Error:
                        template_dict['message'] = \
                            'Could not create new %s.' % self.thing_descriptors.get(edit)
                    else:
                        template_dict['message'] = '%s created.' % self.thing_descriptors.get(edit)
                        template_dict['show_form'] = False
                else:
                    try:
                        if(edit=="news"):
                             thing = NewsArticleNew.get(Key(key))
                             thing.title = form_data['title']
                             thing.author = Member.get_by_id(int(post['author']))
                             thing.date = this_date
                             thing.body = form_data['body']

                        elif(edit=="talk"):

                             thing = TalkNew.get(Key(key))
                             thing.title = form_data['title']
                             thing.date = this_date
                             thing.body = form_data['body']

                        elif(edit=="hack"):

                             thing = Hack.get(Key(key))
                             thing.title = form_data['title']
                             thing.date = this_date
                             thing.body = form_data['body']

                        if(self.request.get("picture")):
                             pictureImage = Image(picture=images.resize(self.request.get("picture"), self.image_height, self.image_width),
                                                   name="no-name",title=" ",alt=" ")
                             if post['picture_title'] :
                                 pictureImage.title=post['picture_title']
                             if post['picture_alt'] :
                                 pictureImage.alt=post['picture_alt']
                             pictureImage.put()
                             thing.picture = pictureImage
                        elif(post['picture_alias']!="none"):
                                  thing.picture=Image.get_by_id(int(post['picture_alias']))

                        if 'delete_picture' in post:
                             thing.picture=None

                    except BadKeyError:
                        template_dict['message'] = \
                            'Could not find %s with key %r.' % (self.thing_descriptors.get(edit),key)
                    else:
                        try:
                            thing.put()
                        except datastore_errors.Error:
                            template_dict['message'] = \
                                'Could not save changes to %s.' % self.thing_descriptors.get(edit)
                        else:
                            template_dict['form_data'] = thing
                            template_dict['message'] = 'Changes saved.'
        self.render_template('edit', template_dict)


class ImageEditHandler(BaseHandler):
    def get(self,key):
        try:
            image = Image.get(Key(key))
            self.render_template('editImage',{'image':image})
        except BadKeyError:
            self.render_template('editImage',{'error':"Image Not Found"})

    def post(self,key):
        try:
            image = Image.get(Key(key))
            post = self.request.POST
            image.name=post['name']
            image.title=post['title']
            image.alt=post['alt']
            image.put()
            self.render_template('editImage',{'image':image})
        except BadKeyError:
            self.render_template('editImage',{'error':"Image Not Found"})

class ImageHandler(RequestHandler):
    def get(self):
        get = self.request.GET
        if 'img_id' in get :
           image = db.get(get['img_id'])
           if image.picture:
               self.response.headers['Content-Type'] = "image/png"
               self.response.out.write(image.picture)
           else:
               self.response.out.write("No image")
        elif 'img_alias' in get :
           image = getImage(get['img_alias'])
           if image :
               self.response.headers['Content-Type'] = "image/png"
               self.response.out.write(image.picture)
           else :
               self.response.out.write("No image")
        else:
            self.response.out.write("No image")

# This handler is a hack to force people to select handles.
class LoginHandler(BaseHandler):

    def get(self):
        if 'url' in self.request.GET:
            member = Member.get_current_member()
            if member.handle.isdigit() and len(member.handle) == 21:
                self.redirect('/account')
            else:
                self.redirect(self.request.GET.getall('url')[0])
        else:
            self.redirect('/')

class MemberHandler(BaseHandler):

    def get(self, handle):
        query = Member.gql('WHERE handle = :1', urllib.unquote(handle))
        member = iter(query).next() if query.count() else None
        member_talks = TalkNew.all().filter('member = ', member)
        self.render_template('member', {
            'member': member,
            'member_talks' : member_talks
        })


class MessagesHandler(BaseHandler):

    def get(self, message_index):
        message_file = None
        try:
            message_file = open('static/messages/%s.html' % message_index)
            self.response.out.write(message_file.read())
        except:
            self.render_template('404',
                {'url': 'message number %s' % message_index})
        finally:
            if message_file is not None:
                message_file.close()


class PaginationHandler(BaseHandler):
    DEF_ERROR_MESSAGE = "That page doesn't exist, why not look at this."
    ITEM_PER_PAGE = 5
    _model = None
    _template = None

    def get(self):
        try:
            page_num = int(self.request.GET.get('page', 0))
        except ValueError:
            page_num = 0
            message = self._DEF_ERROR_MESSAGE
        else:
            message = None

        items = self._model.all().order('-date');

        last_page = items.count() // self.ITEM_PER_PAGE

        if page_num > last_page:
            page_num = last_page
            message = self._DEF_ERROR_MESSAGE
        elif page_num < 0:
            page_num = 0
            message = self._DEF_ERROR_MESSAGE

        pagination_dict = {'num': page_num,
                           'prev': page_num - 1,
                           'next': page_num + 1,
                           'hasNext': page_num != last_page,
                           'hasPrev': page_num != 0}

        first_page_item = page_num * self.ITEM_PER_PAGE
        last_page_item = (page_num + 1) * self.ITEM_PER_PAGE

        self.render_template(self._template,
            {'content_list': items.fetch(last_page_item, first_page_item),
             'message': message,
             'pagedata': pagination_dict})

## Simple Handlers, in alphabetical order

class CalendarHandler(BaseHandler):

    def get(self):
        self.render_template('calendar')


class ContactHandler(BaseHandler):
    def get(self):
        self.render_template('contact')

class CommitteeHandler(BaseHandler):
    def get(self):
        self.render_template('committee')

class FAQHandler(BaseHandler):
      def get(self):
        self.render_template('faq')


class FileNotFoundHandler(BaseHandler):
    def get(self, url=None):
        self.render_template('404', {'url': url})

class HackathonHandler(PaginationHandler):
    _model = Hack
    _template = 'hack-a-thon'


class ManualHandler(BaseHandler):
    def get(self):
        self.render_template('manual')

class NewsHandler(PaginationHandler):
    _model = NewsArticleNew
    _template = 'news'


class TalksHandler(PaginationHandler):
    _model = TalkNew
    _template = 'talks'

