#!/usr/bin/env python
"""Convert PEP's to (X)HTML - courtesy of /F

Usage: %(PROGRAM)s [options] [peps]

Options:

    -u/--user
        python.org username

    -b/--browse
        After generating the HTML, direct your web browser to view it
        (using the Python webbrowser module).  If both -i and -b are
        given, this will browse the on-line HTML; otherwise it will
        browse the local HTML.  If no pep arguments are given, this
        will browse PEP 0.

    -i/--install
        After generating the HTML, install it and the plain text source file
        (.txt) on python.org.  In that case the user's name is used in the scp
        and ssh commands, unless "-u username" is given (in which case, it is
        used instead).  Without -i, -u is ignored.

    -q/--quiet
        Turn off verbose messages.

    -h/--help
        Print this help message and exit.

The optional argument `peps' is a list of either pep numbers or .txt files.
"""

import sys
import os
import re
import cgi
import glob
import getopt
import errno
import random
import time

REQUIRES = {'python': '2.2',
            'docutils': '0.2.1'}
PROGRAM = sys.argv[0]
RFCURL = 'http://www.faqs.org/rfcs/rfc%d.html'
PEPURL = 'pep-%04d.html'
PEPCVSURL = ('http://cvs.sourceforge.net/cgi-bin/viewcvs.cgi/python/python'
             '/nondist/peps/pep-%04d.txt')
PEPDIRRUL = 'http://www.python.org/peps/'


HOST = "www.python.org"                    # host for update
HDIR = "/ftp/ftp.python.org/pub/www.python.org/peps" # target host directory
LOCALVARS = "Local Variables:"

# The generated HTML doesn't validate -- you cannot use <hr> and <h3> inside
# <pre> tags.  But if I change that, the result doesn't look very nice...
DTD = ('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN"\n'
       '                      "http://www.w3.org/TR/REC-html40/loose.dtd">')

fixpat = re.compile("((http|ftp):[-_a-zA-Z0-9/.+~:?#$=&,]+)|(pep-\d+(.txt)?)|"
                    "(RFC[- ]?(?P<rfcnum>\d+))|"
                    "(PEP\s+(?P<pepnum>\d+))|"
                    ".")

EMPTYSTRING = ''
SPACE = ' '
COMMASPACE = ', '



def usage(code, msg=''):
    print >> sys.stderr, __doc__ % globals()
    if msg:
        print >> sys.stderr, msg
    sys.exit(code)



def fixanchor(current, match):
    text = match.group(0)
    link = None
    if text.startswith('http:') or text.startswith('ftp:'):
        # Strip off trailing punctuation.  Pattern taken from faqwiz.
        ltext = list(text)
        while ltext:
            c = ltext.pop()
            if c not in '();:,.?\'"<>':
                ltext.append(c)
                break
        link = EMPTYSTRING.join(ltext)
    elif text.startswith('pep-') and text <> current:
        link = os.path.splitext(text)[0] + ".html"
    elif text.startswith('PEP'):
        pepnum = int(match.group('pepnum'))
        link = PEPURL % pepnum
    elif text.startswith('RFC'):
        rfcnum = int(match.group('rfcnum'))
        link = RFCURL % rfcnum
    if link:
        return '<a href="%s">%s</a>' % (link, cgi.escape(text))
    return cgi.escape(match.group(0)) # really slow, but it works...



NON_MASKED_EMAILS = [
    'peps@python.org',
    'python-list@python.org',
    'python-dev@python.org',
    ]

def fixemail(address, pepno):
    if address.lower() in NON_MASKED_EMAILS:
        # return hyperlinked version of email address
        return linkemail(address, pepno)
    else:
        # return masked version of email address
        parts = address.split('@', 1)
        return '%s&#32;&#97;t&#32;%s' % (parts[0], parts[1])


def linkemail(address, pepno):
    parts = address.split('@', 1)
    return ('<a href="mailto:%s&#64;%s?subject=PEP%%20%s">'
            '%s&#32;&#97;t&#32;%s</a>'
            % (parts[0], parts[1], pepno, parts[0], parts[1]))


def fixfile(inpath, input_lines, outfile):
    from email.Utils import parseaddr
    basename = os.path.basename(inpath)
    infile = iter(input_lines)
    # convert plain text pep to minimal XHTML markup
    print >> outfile, DTD
    print >> outfile, '<html>'
    print >> outfile, '<head>'
    # head
    header = []
    pep = ""
    title = ""
    for line in infile:
        if not line.strip():
            break
        if line[0].strip():
            if ":" not in line:
                break
            key, value = line.split(":", 1)
            value = value.strip()
            header.append((key, value))
        else:
            # continuation line
            key, value = header[-1]
            value = value + line
            header[-1] = key, value
        if key.lower() == "title":
            title = value
        elif key.lower() == "pep":
            pep = value
    if pep:
        title = "PEP " + pep + " -- " + title
    if title:
        print >> outfile, '  <title>%s</title>' % cgi.escape(title)
    r = random.choice(range(64))
    print >> outfile, (
        '  <link rel="STYLESHEET" href="style.css" type="text/css">\n'
        '</head>\n'
        '<body bgcolor="white" marginwidth="0" marginheight="0">\n'
        '<table class="navigation" cellpadding="0" cellspacing="0"\n'
        '       width="100%%" border="0">\n'
        '<tr><td class="navicon" width="150" height="35">\n'
        '<a href="../" title="Python Home Page">\n'
        '<img src="../pics/PyBanner%03d.gif" alt="[Python]"\n'
        ' border="0" width="150" height="35" /></a></td>\n'
        '<td class="textlinks" align="left">\n'
        '[<b><a href="../">Python Home</a></b>]' % r)
    if basename <> 'pep-0000.txt':
        print >> outfile, '[<b><a href=".">PEP Index</a></b>]'
    if pep:
        try:
            print >> outfile, ('[<b><a href="pep-%04d.txt">PEP Source</a>'
                               '</b>]' % int(pep))
        except ValueError, error:
            print >> sys.stderr, '%s: %s' % (error.__class__.__name__, error)
    print >> outfile, '</td></tr></table>'
    print >> outfile, '<div class="header">\n<table border="0">'
    for k, v in header:
        if k.lower() in ('author', 'discussions-to'):
            mailtos = []
            for part in re.split(',\s*', v):
                if '@' in part:
                    realname, addr = parseaddr(part)
                    if k.lower() == 'discussions-to':
                        m = linkemail(addr, pep)
                    else:
                        m = fixemail(addr, pep)
                    mailtos.append('%s &lt;%s&gt;' % (realname, m))
                elif part.startswith('http:'):
                    mailtos.append(
                        '<a href="%s">%s</a>' % (part, part))
                else:
                    mailtos.append(part)
            v = COMMASPACE.join(mailtos)
        elif k.lower() in ('replaces', 'replaced-by', 'requires'):
            otherpeps = ''
            for otherpep in re.split(',?\s+', v):
                otherpep = int(otherpep)
                otherpeps += '<a href="pep-%04d.html">%i</a> ' % (otherpep,
                                                                  otherpep)
            v = otherpeps
        elif k.lower() in ('last-modified',):
            date = v or time.strftime('%d-%b-%Y',
                                      time.localtime(os.stat(inpath)[8]))
            try:
                url = PEPCVSURL % int(pep)
                v = '<a href="%s">%s</a> ' % (url, cgi.escape(date))
            except ValueError, error:
                v = date
        elif k.lower() in ('content-type',):
            url = PEPURL % 9
            pep_type = v or 'text/plain'
            v = '<a href="%s">%s</a> ' % (url, cgi.escape(pep_type))
        else:
            v = cgi.escape(v)
        print >> outfile, '  <tr><th>%s:&nbsp;</th><td>%s</td></tr>' \
              % (cgi.escape(k), v)
    print >> outfile, '</table>'
    print >> outfile, '</div>'
    print >> outfile, '<hr />'
    print >> outfile, '<div class="content">'
    need_pre = 1
    for line in infile:
        if line[0] == '\f':
            continue
        if line.strip() == LOCALVARS:
            break
        if line[0].strip():
            if line.strip() == LOCALVARS:
                break
            if not need_pre:
                print >> outfile, '</pre>'
            print >> outfile, '<h3>%s</h3>' % line.strip()
            need_pre = 1
        elif not line.strip() and need_pre:
            continue
        else:
            # PEP 0 has some special treatment
            if basename == 'pep-0000.txt':
                parts = line.split()
                if len(parts) > 1 and re.match(r'\s*\d{1,4}', parts[1]):
                    # This is a PEP summary line, which we need to hyperlink
                    url = PEPURL % int(parts[1])
                    if need_pre:
                        print >> outfile, '<pre>'
                        need_pre = 0
                    print >> outfile, re.sub(
                        parts[1],
                        '<a href="%s">%s</a>' % (url, parts[1]),
                        line, 1),
                    continue
                elif parts and '@' in parts[-1]:
                    # This is a pep email address line, so filter it.
                    url = fixemail(parts[-1], pep)
                    if need_pre:
                        print >> outfile, '<pre>'
                        need_pre = 0
                    print >> outfile, re.sub(
                        parts[-1], url, line, 1),
                    continue
            line = fixpat.sub(lambda x, c=inpath: fixanchor(c, x), line)
            if need_pre:
                print >> outfile, '<pre>'
                need_pre = 0
            outfile.write(line)
    if not need_pre:
        print >> outfile, '</pre>'
    print >> outfile, '</div>'
    print >> outfile, '</body>'
    print >> outfile, '</html>'


docutils_options = None
"""Option value object used by Docutils.  Can be set by the client application
when this module is imported."""

def fix_rst_pep(inpath, input_lines, outfile):
    from docutils import core, io
    pub = core.Publisher()
    pub.set_reader(reader_name='pep', parser_name='restructuredtext',
                   parser=None)
    pub.set_writer(writer_name='pep_html')
    if docutils_options:
        options = docutils_options
        pub.options = options
    else:
        options = pub.set_options()
    options._source = inpath
    options._destination = outfile.name
    pub.source = io.StringInput(
        options, source=''.join(input_lines), source_path=inpath)
    pub.destination = io.FileOutput(
        options, destination=outfile, destination_path=outfile.name,
        autoclose=0)
    pub.publish()


def get_pep_type(input_lines):
    """
    Return the Content-Type of the input.  "text/plain" is the default.
    Return ``None`` if the input is not a PEP.
    """
    pep_type = None
    for line in input_lines:
        line = line.rstrip().lower()
        if not line:
            # End of the RFC 2822 header (first blank line).
            break
        elif line.startswith('content-type: '):
            pep_type = line.split()[1] or 'text/plain'
            break
        elif line.startswith('pep: '):
            # Default PEP type, used if no explicit content-type specified:
            pep_type = 'text/plain'
    return pep_type


def get_input_lines(inpath):
    try:
        infile = open(inpath)
    except IOError, e:
        if e.errno <> errno.ENOENT: raise
        print >> sys.stderr, 'Error: Skipping missing PEP file:', e.filename
        sys.stderr.flush()
        return None, None
    lines = infile.read().splitlines(1) # handles x-platform line endings
    infile.close()
    return lines


def find_pep(pep_str):
    """Find the .txt file indicated by a cmd line argument"""
    if os.path.exists(pep_str):
        return pep_str
    num = int(pep_str)
    return "pep-%04d.txt" % num

def make_html(inpath, verbose=0):
    input_lines = get_input_lines(inpath)
    pep_type = get_pep_type(input_lines)
    if pep_type is None:
        print >> sys.stderr, 'Error: Input file %s is not a PEP.' % inpath
        sys.stdout.flush()
        return None
    elif not PEP_TYPE_DISPATCH.has_key(pep_type):
        print >> sys.stderr, ('Error: Unknown PEP type for input file %s: %s'
                              % (inpath, pep_type))
        sys.stdout.flush()
        return None
    elif PEP_TYPE_DISPATCH[pep_type] == None:
        pep_type_error(inpath, pep_type)
        return None
    outpath = os.path.splitext(inpath)[0] + ".html"
    if verbose:
        print inpath, "(%s)" % pep_type, "->", outpath
        sys.stdout.flush()
    outfile = open(outpath, "w")
    PEP_TYPE_DISPATCH[pep_type](inpath, input_lines, outfile)
    outfile.close()
    os.chmod(outfile.name, 0664)
    return outpath

def push_pep(htmlfiles, txtfiles, username, verbose):
    if verbose:
        quiet = ""
    else:
        quiet = "-q"
    if username:
        username = username + "@"
    target = username + HOST + ":" + HDIR
    files = htmlfiles[:]
    files.extend(txtfiles)
    files.append("style.css")
    files.append("pep.css")
    filelist = SPACE.join(files)
    rc = os.system("scp %s %s %s" % (quiet, filelist, target))
    if rc:
        sys.exit(rc)
    rc = os.system("ssh %s%s chmod 664 %s/*" % (username, HOST, HDIR))
    if rc:
        sys.exit(rc)


PEP_TYPE_DISPATCH = {'text/plain': fixfile,
                     'text/x-rst': fix_rst_pep}
PEP_TYPE_MESSAGES = {}

def check_requirements():
    # Check Python:
    try:
        from email.Utils import parseaddr
    except ImportError:
        PEP_TYPE_DISPATCH['text/plain'] = None
        PEP_TYPE_MESSAGES['text/plain'] = (
            'Python %s or better required for "%%(pep_type)s" PEP '
            'processing; %s present (%%(inpath)s).'
            % (REQUIRES['python'], sys.version.split()[0]))
    # Check Docutils:
    try:
        import docutils
    except ImportError:
        PEP_TYPE_DISPATCH['text/x-rst'] = None
        PEP_TYPE_MESSAGES['text/x-rst'] = (
            'Docutils not present for "%(pep_type)s" PEP file %(inpath)s.  '
            'See README.txt for installation.')
    else:
        if docutils.__version__ < REQUIRES['docutils']:
            PEP_TYPE_DISPATCH['text/x-rst'] = None
            PEP_TYPE_MESSAGES['text/x-rst'] = (
                'Docutils must be reinstalled for "%%(pep_type)s" PEP '
                'processing (%%(inpath)s).  Version %s or better required; '
                '%s present.  See README.txt for installation.'
                % (REQUIRES['docutils'], docutils.__version__))

def pep_type_error(inpath, pep_type):
    print >> sys.stderr, 'Error: ' + PEP_TYPE_MESSAGES[pep_type] % locals()
    sys.stdout.flush()


def browse_file(pep):
    import webbrowser
    file = find_pep(pep)
    if file.endswith(".txt"):
        file = file[:-3] + "html"
    file = os.path.abspath(file)
    url = "file:" + file
    webbrowser.open(url)

def browse_remote(pep):
    import webbrowser
    file = find_pep(pep)
    if file.endswith(".txt"):
        file = file[:-3] + "html"
    url = PEPDIRRUL + file
    webbrowser.open(url)


def main(argv=None):
    # defaults
    update = 0
    username = ''
    verbose = 1
    browse = 0

    check_requirements()

    if argv is None:
        argv = sys.argv[1:]

    try:
        opts, args = getopt.getopt(
            argv, 'bihqu:',
            ['browse', 'install', 'help', 'quiet', 'user='])
    except getopt.error, msg:
        usage(1, msg)

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage(0)
        elif opt in ('-i', '--install'):
            update = 1
        elif opt in ('-u', '--user'):
            username = arg
        elif opt in ('-q', '--quiet'):
            verbose = 0
        elif opt in ('-b', '--browse'):
            browse = 1

    if args:
        peptxt = []
        html = []
        for pep in args:
            file = find_pep(pep)
            peptxt.append(file)
            newfile = make_html(file, verbose=verbose)
            if newfile:
                html.append(newfile)
            if browse and not update:
                browse_file(pep)
    else:
        # do them all
        peptxt = []
        html = []
        files = glob.glob("pep-*.txt")
        files.sort()
        for file in files:
            peptxt.append(file)
            newfile = make_html(file, verbose=verbose)
            if newfile:
                html.append(newfile)
        if browse and not update:
            browse_file("0")

    if update:
        push_pep(html, peptxt, username, verbose)
        if browse:
            if args:
                for pep in args:
                    browse_remote(pep)
            else:
                browse_remote("0")



if __name__ == "__main__":
    main()
