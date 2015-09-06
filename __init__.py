import os, sys, types, datetime, yaml
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

    def copy_build_status(self, old_content, new_content):
        start_index = old_content.find('<h2>Build Status</h2>')
        temp_content = old_content[start_index:]
        stop_index = temp_content.find('<h2>Copyright</h2>') 
        build_status_block = temp_content[:stop_index]
    
        start_index = new_content.find('<h2>Build Status</h2>')
        stop_index = new_content.find('<h2>Copyright</h2>')
    
        new_content = new_content[:start_index] + build_status_block + new_content[stop_index:]
        return new_content

    @property
    def cache_path(self):
        return os.path.join(wasanbon.home_path, 'cache')
    
    @property
    def cache_file_path(self):
        return os.path.join(self.cache_path, 'wordpress_cache.txt')
    
    @manifest
    def cache(self, argv):
        """ Update Wordpress Site """
        #self.parser.add_option('-f', '--force', help='Force option (default=False)', default=False, action='store_true', dest='force_flag')


        options, argv = self.parse_args(argv[:])
        verbose = options.verbose_flag # This is default option


        setting_filename = 'setting.txt'
        
        if not os.path.isdir(self.cache_path):
            os.mkdir(self.cache_path)
        
        f = open(self.cache_file_path, 'w')

        wp = self._initialize(setting_filename, verbose=verbose)
        all_posts = self._load_all_posts(wp, verbose=verbose)
        for p in all_posts:
            f.write('"%s":\n' % p.title)
            f.write('  id : %s\n' %  p.id)
        f.close()
        return 0

    def _initialize(self, setting_filename, verbose=False):
        from wordpress_xmlrpc import Client
        user, passwd, url = load_setting(setting_filename, verbose=verbose)
        wp = Client(url + '/xmlrpc.php', user, passwd)    
        return wp

    def _load_all_posts(self, wp, verbose=False):
        from wordpress_xmlrpc.methods.posts import GetPosts
        all_posts = []
        sys.stdout.write(' - Loading All Posts...\n')
        offset = 0
        increment = 20
        while True:
            my_posts = wp.call(GetPosts({'number': increment, 'offset': offset}))
            if len(my_posts) == 0:
                break  # no more posts returned
            all_posts = all_posts + my_posts
            offset = offset + increment
            sys.stdout.write(' - OK.\n')
        return all_posts

        
    @manifest 
    def upload(self, argv):
        """ Update Wordpress Site """
        #self.parser.add_option('-f', '--force', help='Force option (default=False)', default=False, action='store_true', dest='force_flag')
        self.parser.add_option('-i', '--i', help='Update Image (default=False)', default=False, action='store_true', dest='image_flag')
        options, argv = self.parse_args(argv[:])
        verbose = options.verbose_flag # This is default option
        upImage = options.image_flag        

        wasanbon.arg_check(argv, 4)
        rtc_name = argv[3]
        if verbose: sys.stdout.write('# Searching RTC (%s)...\n' % rtc_name)
        package = admin.package.get_package_from_path(os.getcwd(), verbose=verbose)
        rtc = admin.rtc.get_rtc_from_package(package, rtc_name, verbose=verbose)

            


        setting_filename = 'setting.txt'
        
        post_id_dict = yaml.load(open(self.cache_file_path, 'r'))

        post_id = -1
        title = '[RTC] ' + rtc_name
        for key, value in post_id_dict.items():
            if key == title:
                post_id = value['id']

        if post_id < 0:
            sys.stdout.write('## Error. Can not find post.\n')
            return -1

        wp = self._initialize(setting_filename, verbose=verbose)
        from wordpress_xmlrpc.methods.posts import GetPost

        if upImage:
            image = mgr.rtcprofile.get_image(rtc.rtcprofile)
            filename = rtc.rtcprofile.basicInfo.name + '.jpg'
            image_path = save_image(image, filename)
            image_info  = upload_image(wp, image_path)
        else:
            image_info = None

        html = mgr.rtcprofile.get_html(rtc)
        old_post = wp.call(GetPost(post_id))
        if old_post:
            html = self.copy_build_status(old_post.content, html)
        
        post(wp, old_post, title, html, rtc.rtcprofile, image_info) 
        
        return 0

rtc_name_tag = '<h2>Name</h2>'
rtc_brief_tag = '<h2>Brief</h2>'

build_in_windows_tag = '<h3>Build in Windows</h3>'
build_in_osx_tag = '<h3>Build in OSX</h3>'
build_in_linux_tag = '<h3>Build in Linux</h3>'
all_posts = []    


def load_setting(setting_filename, verbose=False):
    import yaml
    user = ""
    url = ""
    passwd = ""
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
    return (user, passwd, url)

def load_all_posts(wp, verbose=False):
    from wordpress_xmlrpc.methods.posts import GetPosts
    all_posts = []
    sys.stdout.write(' - Loading All Posts...\n')
    offset = 0
    increment = 20
    while True:
        my_posts = wp.call(GetPosts({'number': increment, 'offset': offset}))
        if len(my_posts) == 0:
                break  # no more posts returned
        all_posts = all_posts + my_posts
        offset = offset + increment
    sys.stdout.write(' - OK.\n')
    return all_posts

def initialize(setting_filename, verbose=False):
    from wordpress_xmlrpc import Client
    user, passwd, url = load_setting(setting_filename, verbose=verbose)
    wp = Client(url + '/xmlrpc.php', user, passwd)    
    global all_posts
    all_posts = load_all_posts(wp, verbose=verbose)
    return wp

def main(setting_filename, build_report_filename, verbose=False):
    import yaml
    
    wp = initialize(setting_filename, verbose=verbose)

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


        filename = rtc.rtcprofile.basicInfo.name + '.jpg'
        image_path = save_image(image, filename)
        image_info  = upload_image(wp, image_path)

        title = '[RTC] ' + rtc.rtcprofile.basicInfo.name
        html  = mgr.rtcprofile.get_html(rtc.rtcprofile.basicInfo.name)
        old_post = load_post(all_posts, title)
        if old_post: # Copy Build Status of other platform from old post.
            new_post_html = copy_build_status(old_post.content, html)
        new_post_html = update_build_status(new_post_html, build_report_filename)
        new_post_html = apply_language_setting(new_post_html)

        post(wp, old_post, title, new_post_html, rtc.rtcprofile, image_info)

        #upload_text(wp, repo.name, rtc.rtcprofile, html, response, build_report_filename=build_report_filename)

    return 0

def save_image(im, filename):
    img_dir = 'image'
    if not os.path.isdir(img_dir):
        os.mkdir(img_dir)
    img_path = os.path.join(os.getcwd(), img_dir, filename)
    if os.path.isfile(img_path):
        os.remove(img_path)
    im.save(img_path)
    return img_path

def upload_image(wp, img_file):
    from wordpress_xmlrpc.compat import xmlrpc_client
    from wordpress_xmlrpc.methods import posts, taxonomies, media
    sys.stdout.write(' - Uploading Image %s\n' % img_file)
    data = {
        'name': os.path.basename(img_file),
        'type': 'image/jpeg',  # mimetype
        }
    
    with open(img_file, 'rb') as img:
        data['bits'] = xmlrpc_client.Binary(img.read())

    response = wp.call(media.UploadFile(data))
    return response


def load_post(all_posts, title):
    for p in all_posts:
        if p.title == title:
            return p
    return None

def upload_text(wp, repo_name, rtcprof, html, img_info = None, test=False, build_report_filename="build_report.yaml"):
    from wordpress_xmlrpc.methods import posts, taxonomies, media
    sys.stdout.write(' - Uploading %s\n' % rtcprof.name)

    editFlag = False
    post = None

    for p in all_posts:
        if p.title == title:
            editFlag = True
            post = p


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

def post(wp, old_post, title, content, rtcprof, img_info):
    from wordpress_xmlrpc import WordPressPost
    from wordpress_xmlrpc.methods.posts import NewPost, EditPost
    if old_post:
        post = old_post
    else:
        post = WordPressPost()

    post.title = title
    post.content = content
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
    if img_info:
        post.thumbnail = img_info['id']
    else:
        post.thumbnail = old_post.thumbnail
    if old_post: # Edit Mode
        wp.call(EditPost(post.id, post))
    else:
        wp.call(NewPost(post))


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

