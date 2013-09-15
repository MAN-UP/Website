import sys

from google.appengine.dist import use_library
use_library('django', '1.2')

from google.appengine.ext.webapp import WSGIApplication
from google.appengine.ext.webapp.template import register_template_library
from google.appengine.ext.webapp.util import run_wsgi_app

from handlers import AccountHandler, AdminHandler, \
    ImageHandler, CalendarHandler, ImageEditHandler,\
    ContactHandler, EditHandler, FAQHandler, FileNotFoundHandler, \
    HackathonHandler, LoginHandler, ManualHandler, MemberHandler, \
    MessagesHandler, NewsHandler, TalksHandler, CommitteeHandler

register_template_library('templatetags.customtags')

application = WSGIApplication(
    ((r'^/$'                             , NewsHandler),
     (r'^/news$'                         , NewsHandler),
     (r'^/account$'                      , AccountHandler),
     (r'^/admin$'                        , AdminHandler),
     (r'^/admin/edit/img$'               , ImageHandler),
     (r'^/admin/edit/([^/]+)$'           , EditHandler),
     (r'^/admin/editImage/img$'          , ImageHandler),
     (r'^/admin/editImage/([^/]+)$'      , ImageEditHandler),
     (r'^/calendar$'                     , CalendarHandler),
     (r'^/contact$'                      , ContactHandler),
     (r'^/committee$'                    , CommitteeHandler),
     (r'^/faq$'                          , FAQHandler),
     (r'^/hack-a-thon$'                  , HackathonHandler),
     (r'^/img$'                          , ImageHandler),
     (r'^/login$'                        , LoginHandler),
     (r'^/manual$'                       , ManualHandler),
     (r'^/members/([^/]+)$'              , MemberHandler),
     (r'^/messages/(\d+)$'               , MessagesHandler),
     (r'^/talks$'                        , TalksHandler),
     (r'(.*)'                            , FileNotFoundHandler)),
     debug=True)

def main(argv=None):
    if argv is None:
        argv = sys.argv
    run_wsgi_app(application)
    return 0

if __name__ == '__main__':
    main()
