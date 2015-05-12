import os, sys, types, datetime
import wasanbon
from wasanbon.core.plugins import PluginFunction, manifest

class Plugin(PluginFunction):

    def __init__(self):
        #PluginFunction.__init__(self)
        super(Plugin, self).__init__()
        pass

    def depends(self):
        return ['admin.environment', 'admin.rtc', 'admin.package', 'mgr.repository', 'mgr.rtcprofile']

    @manifest
    def update(self, argv):
        """ Update Wordpress Site """
        #self.parser.add_option('-f', '--force', help='Force option (default=False)', default=False, action='store_true', dest='force_flag')
        options, argv = self.parse_args(argv[:])
        verbose = options.verbose_flag # This is default option
        #force   = options.force_flag

        setting_filename = 'setting.txt'
        build_report_filename = 'build_report.yaml'

        main(setting_filename, build_report_filename, verbose=verbose)
        return 0
rtc_name_tag = '<h2>Name</h2>'
rtc_brief_tag = '<h2>Brief</h2>'

build_in_windows_tag = '<h3>Build in Windows</h3>'
build_in_osx_tag = '<h3>Build in OSX</h3>'
build_in_linux_tag = '<h3>Build in Linux</h3>'
all_posts = []    

def main(setting_filename, build_report_filename, verbose=False):
    from wordpress_xmlrpc import Client, WordPressPost
    from wordpress_xmlrpc.methods.posts import GetPosts, NewPost
    from wordpress_xmlrpc.methods.users import GetUserInfo
    from wordpress_xmlrpc.methods import posts, taxonomies, media
    from wordpress_xmlrpc.compat import xmlrpc_client
    import yaml
    
    if setting_filename in os.listdir(os.getcwd()):
        setting = yaml.load(open(setting_filename, 'r'))
        user = setting['user']
        passwd = setting['passwd']
        url = setting['url']
    else:
        print 'User:', 
        user = raw_input()
        print 'Pass:',
        passwd = raw_input()
        print 'URL :',
        url = raw_input()
        if url.endswith('/'):
            url = url[0:-1]

    wp = Client(url + '/xmlrpc.php', user, passwd)
    global all_posts
    offset = 0
    increment = 20
    sys.stdout.write(' - Loading All Posts...\n')
    while True:
        my_posts = wp.call(posts.GetPosts({'number': increment, 'offset': offset}))
        if len(my_posts) == 0:
                break  # no more posts returned
        all_posts = all_posts + my_posts
        offset = offset + increment
    sys.stdout.write(' - OK.\n')
    #yaml.dump(all_posts)

    package = admin.package.get_package_from_path(os.getcwd())
    #rtcs = admin.rtc.get_rtcs_from_package(package, verbose=verbose)
    build_report = yaml.load(open(build_report_filename, 'r'))
    for name, value in build_report.items():
        sys.stdout.write('Build Report of RTC (%s) found.\n' % name)
        try:
            rtc = admin.rtc.get_rtc_from_package(package, name, verbose=verbose)
        except wasanbon.RTCNotFoundException, ex:
            sys.stdout.write('## Error. RTC (%s) Not Found.\n' % name)
            continue
        repo = mgr.repository.get_registered_repository_from_rtc(rtc, verbose=verbose)
        image = mgr.rtcprofile.get_image(rtc.rtcprofile)
        html  = mgr.rtcprofile.get_html(rtc.rtcprofile.basicInfo.name)

        image_path = save_image(rtc.rtcprofile, image)
        response = upload_image(wp, rtc.rtcprofile, image_path)
        upload_text(wp, repo.name, rtc.rtcprofile, html, response, build_report_filename=build_report_filename)

    return 0

def save_image(rtcprofile, im):
    img_dir = 'image'
    if not os.path.isdir(img_dir):
        os.mkdir(img_dir)
    img_path = os.path.join(os.getcwd(), img_dir, rtcprofile.basicInfo.name + '.jpg')
    if os.path.isfile(img_path):
        os.remove(img_path)
    im.save(img_path)
    return img_path

def upload_image(wp, rtcprof, img_file):
    from wordpress_xmlrpc.compat import xmlrpc_client
    from wordpress_xmlrpc.methods import posts, taxonomies, media
    sys.stdout.write(' - Uploading Image %s\n' % rtcprof.name)
    data = {
        'name': os.path.basename(img_file),
        'type': 'image/jpeg',  # mimetype
        }
    
    with open(img_file, 'rb') as img:
        data['bits'] = xmlrpc_client.Binary(img.read())

    response = wp.call(media.UploadFile(data))
    # response == {
    #       'id': 6,
    #       'file': 'picture.jpg'
    #       'url': 'http://www.example.com/wp-content/uploads/2012/04/16/picture.jpg',
    #       'type': 'image/jpeg',
    # }
    return response

def upload_text(wp, repo_name, rtcprof, html, img_info = None, test=False, build_report_filename="build_report.yaml"):
    from wordpress_xmlrpc.methods import posts, taxonomies, media
    sys.stdout.write(' - Uploading %s\n' % rtcprof.name)
    title = '[RTC] ' + repo_name #rtcprof.name
    editFlag = False
    post = None

    if test:
        open(title + ".html", "w").write(html)
        return

    for p in all_posts:
        if p.title == title:
            editFlag = True
            post = p
            html = copy_build_status(post.content, html)

            break

    html = update_build_status(html, build_report_filename)
    if not editFlag:
        post = WordPressPost()
        post.title = title
        post.content = apply_language_setting(html)
        post.terms_names = {
            'post_tag': [rtcprof.name, 'RTC'],
            'category': ['RTComponents']
            }
        post.slug = rtcprof.name
        n = datetime.datetime.now()
        day = n.day
        hour = n.hour
        if n.hour < 9:
            day = day -1
            hour = hour + 24 
        post.date = datetime.datetime(n.year, n.month, day, hour-9, n.minute, n.second)
        post.post_status = 'publish'
        post.thumbnail = img_info['id']
        post.id = wp.call(NewPost(post))
        return 
    else: # Edit Flag
        #post = WordPressPost()
        post.title = title
        post.content = apply_language_setting(html)
        post.terms_names = {
            'post_tag': [rtcprof.name, 'RTC'],
            'category': ['RTComponents']
            }
        post.slug = rtcprof.name
        n = datetime.datetime.now()
        day = n.day
        hour = n.hour
        if n.hour < 9:
            day = day -1
            hour = hour + 24 
        post.date = datetime.datetime(n.year, n.month, day, hour-9, n.minute, n.second)
        post.post_status = 'publish'
        post.thumbnail = img_info['id']
        wp.call(posts.EditPost(post.id, post))


def copy_build_status(old_content, new_content):
    start_index = old_content.find('<h2>Build Status</h2>')
    temp_content = old_content[start_index:]
    stop_index = temp_content.find('<h2>Copyright</h2>') 
    build_status_block = temp_content[:stop_index]
    
    start_index = new_content.find('<h2>Build Status</h2>')
    stop_index = new_content.find('<h2>Copyright</h2>')
    
    new_content = new_content[:start_index] + build_status_block + new_content[stop_index:]
    return new_content

def update_build_status(content, build_report_filename):
    import yaml
    start_index = content.find(rtc_name_tag)
    stop_index = content.find(rtc_brief_tag)
    rtc_name = content[start_index + len(rtc_name_tag):stop_index].strip()
    
    if sys.platform == 'win32':
        start_index = content.find(build_in_windows_tag)
        stop_index = content.find(build_in_osx_tag)
        tag = build_in_windows_tag
    elif sys.platform == 'darwin':
        start_index = content.find(build_in_osx_tag)
        stop_index = content.find(build_in_linux_tag)
        tag = build_in_osx_tag
    else:
        start_index = content.find(build_in_linux_tag)
        stop_index = content.find('<h2>Copyright</h2>')
        tag = build_in_linux_tag
        pass

    print ' -- Checking Build Status of (%s)' % rtc_name
    status = -1
    if os.path.isfile(build_report_filename):
        f = open(build_report_filename, 'r')
        d = yaml.load(f)
        if type(d) == types.DictType:
            if rtc_name in d.keys():
                status = d[rtc_name]['status']
                print ' -- RTC %s is build (%d)' % (rtc_name, status)
                if status == 0:
                    status_str = 'Success (' + d[rtc_name]['date'] + ')' 
                else:
                    status_str = 'Failed (' + d[rtc_name]['date'] + ')'
                content = content[0:start_index] + tag + '\n' + status_str + '\n' + content[stop_index:]
    
    return content

def apply_language_setting(html):
    text = html.split('<!--more-->')
    content = '<!--:en-->'+text[0]+'<!--:--><!--:ja-->'+text[0]+'<!--:-->' + \
        '<!--more-->' + '<!--:en-->'+text[1]+'<!--:--><!--:ja-->'+text[1]+'<!--:-->'
    return content

