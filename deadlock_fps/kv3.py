"""Lossless editor for text KV3 objects, including comments and opaque typed values."""
import json,re
from dataclasses import dataclass,field

TOKEN=re.compile(r'\ufeff|<!--.*?-->|//[^\r\n]*|/\*.*?\*/|\s+|"(?:\\.|[^"\\])*"|[{}\[\]=,:]|[^\s{}\[\]=,:"/]+',re.S)
@dataclass
class Node:
    key:str
    start:int
    end:int
    value_start:int
    value_end:int
    kind:str
    value:object=None
    children:list=field(default_factory=list)
    close:int=0

def parse(text):
    if not re.match(r'\ufeff?\s*<!--\s*kv3\s+encoding:text:',text):raise ValueError('ملف الأبطال ليس بصيغة KV3 النصية المدعومة.')
    tokens=[];end=0
    for match in TOKEN.finditer(text):
        if match.start()!=end:raise ValueError('رموز غير مدعومة في ملف الأبطال.')
        end=match.end();s=match[0]
        if s.isspace() or s=='\ufeff' or s.startswith(('<!--','//','/*')):continue
        tokens.append(match)
    if end!=len(text):raise ValueError('ملف الأبطال غير مكتمل.')
    pos=0
    def take(value=None):
        nonlocal pos
        if pos>=len(tokens) or value is not None and tokens[pos][0]!=value:raise ValueError('بنية KV3 غير صالحة.')
        token=tokens[pos];pos+=1;return token
    def value(depth=0):
        if depth>64:raise ValueError('ملف إعدادات متداخل أكثر من المسموح.')
        token=take();s=token[0]
        if s=='{':
            nodes=[]
            while pos<len(tokens) and tokens[pos][0]!='}':
                if tokens[pos][0]==',':take();continue
                key=take();name=json.loads(key[0]) if key[0].startswith('"') else key[0]
                if not re.fullmatch(r'[A-Za-z0-9_.-]+',name):raise ValueError('اسم إعداد غير مدعوم.')
                take('=');a,b,kind,val,children,close=value(depth+1)
                nodes.append(Node(name,key.start(),b,a,b,kind,val,children,close))
            closing=take('}');return token.start(),closing.end(),'object',None,nodes,closing.start()
        if s=='[':
            while pos<len(tokens) and tokens[pos][0]!=']':
                if tokens[pos][0]==',':take();continue
                value(depth+1)
            closing=take(']');return token.start(),closing.end(),'array',None,[],closing.start()
        if s in ('}',']','=',',',':'):raise ValueError('قيمة KV3 غير صالحة.')
        if pos<len(tokens) and tokens[pos][0]==':':
            take(':');_,b,_,_,_,_=value(depth+1);return token.start(),b,'typed',None,[],0
        val=json.loads(s) if s.startswith('"') else s
        return token.start(),token.end(),'scalar',val,[],0
    _,_,kind,_,children,close=value()
    if pos!=len(tokens) or kind!='object':raise ValueError('جذر KV3 غير صالح.')
    return Node('',0,len(text),0,len(text),'object',children=children,close=close)

def section(text,path):
    node=parse(text)
    for name in path:
        matches=[n for n in node.children if n.key==name]
        if len(matches)!=1 or matches[0].kind!='object':raise ValueError('قسم مفقود أو مكرر: '+name)
        node=matches[0]
    return node

def fields(text,path):
    result={}
    for n in section(text,path).children:
        if n.key in result:raise ValueError('مفتاح مكرر في ملف الأبطال: '+n.key)
        result[n.key]=n.value if n.kind=='scalar' else n
    return result

def update(text,path,values):
    node=section(text,path);edits=[];found=set()
    for n in node.children:
        if n.key not in values:continue
        if n.key in found or n.kind!='scalar':raise ValueError('إعداد مكرر أو غير بسيط: '+n.key)
        found.add(n.key);v=values[n.key]
        if v is None:edits.append((n.start,n.end,''))
        elif str(n.value)!=str(v):edits.append((n.value_start,n.value_end,json.dumps(str(v))))
    newline='\r\n' if '\r\n' in text else '\n'
    extra=''.join(newline+'\t\t'+k+' = '+json.dumps(str(v)) for k,v in values.items() if k not in found and v is not None)
    if extra:edits.append((node.close,node.close,extra+newline+'\t'))
    for a,b,v in sorted(edits,reverse=True):text=text[:a]+v+text[b:]
    parse(text);return text
