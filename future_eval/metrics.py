"""Small CPU-only metrics. Diagnostics never replace frozen correctness scores."""
from collections import Counter
from fractions import Fraction
import ast
import math
import re
import sqlite3
import time

LABELS = {'boolq':('yes','no'), 'snli':('entailment','neutral','contradiction'),
          'anli':('entailment','neutral','contradiction'), 'scitail':('entailment','neutral'),
          'wiqa':('more','less','no effect')}


def wilson(correct, total):
    if not total:return None
    z=1.95996398454; p=correct/total; d=1+z*z/total
    mid=(p+z*z/(2*total))/d
    radius=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/d
    return [max(0,mid-radius),min(1,mid+radius)]


def label_diagnostic(source, generated):
    """Accept only a whole known label with trivial punctuation; no substring rescue."""
    text=generated.strip().casefold()
    text=re.sub(r'^(answer|label)\s*:\s*','',text).strip().rstrip('.!').strip()
    return text if text in LABELS.get(source,()) else None


def arithmetic(expr):
    """Bounded arithmetic parser; never eval arbitrary model-generated Python."""
    if len(expr)>100:raise ValueError('Expression too long')
    tree=ast.parse(expr,mode='eval')
    if len(list(ast.walk(tree)))>40:raise ValueError('Expression too complex')
    def visit(n):
        if isinstance(n,ast.Expression):return visit(n.body)
        if isinstance(n,ast.Constant) and type(n.value) in (int,float):
            value=Fraction(str(n.value))
        elif isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub)):
            value=visit(n.operand)*(1 if isinstance(n.op,ast.UAdd) else -1)
        elif isinstance(n,ast.BinOp) and isinstance(n.op,(ast.Add,ast.Sub,ast.Mult,ast.Div)):
            a,b=visit(n.left),visit(n.right)
            if isinstance(n.op,ast.Add):value=a+b
            elif isinstance(n.op,ast.Sub):value=a-b
            elif isinstance(n.op,ast.Mult):value=a*b
            else:value=a/b
        else:raise ValueError('Unsupported arithmetic')
        if abs(value)>10**30 or value.denominator>10**30:raise ValueError('Arithmetic out of bounds')
        return value
    return visit(tree)


def error_tags(row):
    """Observable symptoms only: wrong answers do not prove a reasoning mechanism."""
    tags=[]; text=row.get('generated','')
    if not text.strip():tags.append('empty_answer')
    if row.get('stop_reason') in {'token_limit','context_exceeded','deadline'}:
        tags.append(row['stop_reason'])
    words=text.split()
    if len(words)>=20:
        grams=[tuple(words[i:i+4]) for i in range(len(words)-3)]
        if len(set(grams))/len(grams)<.55:tags.append('repetition')
    if row.get('correct') is False:
        clean=label_diagnostic(row['source'],text)
        if clean==row['expected'].strip().casefold():tags.append('trivial_label_format_only')
        elif row['source'] in LABELS:
            tags.append('wrong_label' if clean else 'label_format_or_content')
        else:tags.append('answer_mismatch_cause_unresolved')
    checked=bad=0
    for expr,value in re.findall(r'<<([^<>]+)=([^<>]+)>>',text):
        try:
            a,b=arithmetic(expr),arithmetic(value)
        except (ValueError,SyntaxError,ZeroDivisionError,OverflowError):continue
        checked+=1;bad+=a!=b
    if bad:tags.append('explicit_arithmetic_inconsistency')
    return {'tags':tags,'arithmetic_equalities_checked':checked,'arithmetic_equalities_wrong':bad}


def sql_result(query, table, seconds=.2, max_rows=10000):
    """Execute one read-only SELECT against supplied data with bounded VM work/output."""
    if len(query)>20000 or not re.match(r'^\s*(SELECT|WITH)\b',query,re.I):
        return {'status':'invalid_query'}
    if len(table['rows'])>10000 or len(table['header'])>100:
        return {'status':'table_limit'}
    quote=lambda s:'"'+str(s).replace('"','""')+'"'
    db=sqlite3.connect(':memory:')
    try:
        db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,1000000)
        columns=', '.join(quote(h)+' '+('REAL' if t=='real' else 'TEXT') for h,t in zip(table['header'],table['types']))
        db.execute('CREATE TABLE data ('+columns+')')
        db.executemany('INSERT INTO data VALUES ('+','.join('?' for _ in table['header'])+')',table['rows'])
        db.execute('PRAGMA query_only=ON')
        # Deny file attachment, pragmas, writes, extension loading and unknown functions.
        functions={'count','sum','avg','min','max','abs','round','lower','upper','length','coalesce','ifnull','substr','substring','like','trim','ltrim','rtrim','nullif','total'}
        def authorize(action,a,b,c,d):
            if action in {sqlite3.SQLITE_SELECT,sqlite3.SQLITE_RECURSIVE}:return sqlite3.SQLITE_OK
            if action==sqlite3.SQLITE_READ and a=='data':return sqlite3.SQLITE_OK
            if action==sqlite3.SQLITE_FUNCTION and (b or '').lower() in functions:return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY
        db.set_authorizer(authorize)
        deadline=time.monotonic()+seconds
        ticks=0
        def progress():
            nonlocal ticks
            ticks+=1
            return int(ticks>1000 or time.monotonic()>=deadline)
        db.set_progress_handler(progress,1000)
        rows=db.execute(query).fetchmany(max_rows+1)
        if len(rows)>max_rows:return {'status':'row_limit'}
        return {'status':'ok','rows':rows}
    except (sqlite3.Error,ValueError,OverflowError) as e:
        return {'status':'sql_error','error':str(e)}
    finally:db.close()


def sql_compare(candidate, reference, table):
    """Single-table execution proxy; duplicate rows matter. Not official WikiSQL scoring."""
    expected=sql_result(reference,table)
    if expected['status']!='ok':return {'status':'reference_failed','detail':expected}
    actual=sql_result(candidate,table)
    if actual['status']!='ok':return {'status':'candidate_failed','detail':actual}
    # Conservative: references with ORDER BY require exact order; otherwise compare bags.
    ordered=bool(re.search(r'\bORDER\s+BY\b',reference,re.I))
    equal=actual['rows']==expected['rows'] if ordered else Counter(actual['rows'])==Counter(expected['rows'])
    return {'status':'match' if equal else 'mismatch','ordered':ordered,
            'reference_rows':len(expected['rows']),'candidate_rows':len(actual['rows']),
            'empty_reference_result':not expected['rows'],
            'limitation':'Single original table; equal results can occur for semantically different queries.'}
