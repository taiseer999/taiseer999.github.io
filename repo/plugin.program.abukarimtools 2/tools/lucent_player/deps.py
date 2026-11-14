import re,sys,os,glob
root=sys.argv[1]; files=sys.argv[2:]
allxml={os.path.basename(f):open(f,encoding='utf-8').read() for f in glob.glob(root+'/xml/*.xml')}
defs_inc={}; defs_var={}; defs_exp={}
for fn,s in allxml.items():
    for m in re.finditer(r'<include name="([^"]+)"',s): defs_inc.setdefault(m.group(1),fn)
    for m in re.finditer(r'<variable name="([^"]+)"',s): defs_var.setdefault(m.group(1),fn)
    for m in re.finditer(r'<expression name="([^"]+)"',s): defs_exp.setdefault(m.group(1),fn)
def body(kind,name):
    fn={'inc':defs_inc,'var':defs_var,'exp':defs_exp}[kind].get(name)
    if not fn: return ''
    s=allxml[fn]; tag={'inc':'include','var':'variable','exp':'expression'}[kind]
    i=s.index('<%s name="%s"'%(tag,name)); j=s.index('</%s>'%tag,i) if kind!='inc' else None
    if kind=='inc':
        depth=0
        for m in re.finditer(r'<include\b[^>]*?(/?)>|</include>',s[i:]):
            if m.group(0).startswith('</'): depth-=1
            elif not m.group(1): depth+=1
            if depth==0: return s[i:i+m.end()]
    return s[i:j]
seen={'inc':set(),'var':set(),'exp':set()}; fonts=set(); colors=set(); tex=set(); scripts=set()
def scan(s):
    for n in re.findall(r'<include(?: [^>]*?)?>([A-Za-z0-9_]+)</include>',s)+re.findall(r'<include content="([^"$]+)"',s):
        if n not in seen['inc']: seen['inc'].add(n); scan(body('inc',n))
    for n in re.findall(r'\$VAR\[([A-Za-z0-9_]+)',s):
        if n not in seen['var']: seen['var'].add(n); scan(body('var',n))
    for n in re.findall(r'\$EXP\[([A-Za-z0-9_]+)',s):
        if n not in seen['exp']: seen['exp'].add(n); scan(body('exp',n))
    fonts.update(re.findall(r'<font>([^<$]+)</font>',s))
    colors.update(re.findall(r'(?:colordiffuse|textcolor|focusedcolor|shadowcolor|disabledcolor|selectedcolor)="?>?([A-Za-z][A-Za-z0-9_]*)',s))
    colors.update(re.findall(r'<(?:textcolor|focusedcolor|shadowcolor|disabledcolor|selectedcolor|colordiffuse)>([A-Za-z][A-Za-z0-9_]*)</',s))
    tex.update(re.findall(r'>([A-Za-z0-9_/\-.]+\.(?:png|jpg|gif))<',s)); tex.update(re.findall(r'"([A-Za-z0-9_/\-.]+\.(?:png|jpg|gif))"',s))
    scripts.update(re.findall(r'scripts/([a-z_]+\.py)',s)); scripts.update(re.findall(r'RunScript\(([^,)]+)',s))
for f in files: scan(allxml[f])
print('includes',len(seen['inc']),'from',sorted({defs_inc.get(n,'??') for n in seen['inc']}))
print('undefined inc',[n for n in seen['inc'] if n not in defs_inc][:20])
print('vars',len(seen['var']),'from',sorted({defs_var.get(n,'??') for n in seen['var']}))
print('exps',len(seen['exp']))
print('fonts',sorted(fonts))
print('colors',sorted(c for c in colors if not re.match(r'^[0-9A-Fa-f]{8}$',c)))
print('textures',len(tex)); print(sorted(tex)[:200])
print('scripts',sorted(scripts))
