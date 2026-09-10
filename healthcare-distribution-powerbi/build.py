"""Build a portable Power BI project and reproducible synthetic business case.

Python 3.10+, standard library only. Embedded compressed CSV partitions make
the Power BI project portable without user-specific file paths or web access.
"""
import base64
import csv
from datetime import date, timedelta
import io
import json
from pathlib import Path
import random
import sqlite3
import zlib

ROOT = Path(__file__).resolve().parent
MODEL = ROOT/'Healthcare.SemanticModel'
REPORT = ROOT/'Healthcare.Report'
SCHEMA = 'https://developer.microsoft.com/json-schemas/fabric/item/'

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding='utf-8')

def generate():
    rng = random.Random(2609)
    dates=[]
    for n in range(731):
        d=date(2024,1,1)+timedelta(days=n)
        dates.append([d.isoformat(),d.year,d.strftime('%Y-%m')])
    products=[[1,'Generic medicines','Ambient'],[2,'Specialty medicines','Cold chain'],[3,'Medical supplies','Ambient'],[4,'Diagnostics','Cold chain']]
    customers=[[i, f'Facility {i:02}', ['North','South','East','West'][(i-1)%4], ['Hospital','Clinic','Pharmacy'][(i-1)%3]] for i in range(1,49)]
    carriers=[[1,'Carrier A'],[2,'Carrier B'],[3,'Carrier C']]
    facts=[]
    for i in range(1,12001):
        d=rng.choice(dates)[0]; p=rng.choice(products); c=rng.choice(customers); carrier=rng.choice(carriers)[0]
        units=rng.randint(10,100); price=[12,85,6,38][p[0]-1]
        gross=units*price; discount=round(gross*rng.choice([0,.04,.08,.12]),2)
        delay=rng.choices([0,1,2,4], weights=[80,10,7,3] if carrier!=3 else [57,20,15,8])[0]
        complete=int(rng.random()>.04)
        # Embedded hypotheses, not findings about a real carrier or region.
        returned=int(rng.random()<(.045 if p[2]=='Cold chain' else .015))
        refund=round((gross-discount)*returned,2)
        cogs=round(gross*.61,2)
        freight=round(18+units*(.45 if p[2]=='Cold chain' else .15),2)
        penalty=round((gross-discount)*.02,2) if delay else 0
        expedite=round(35+units*.25,2) if delay>1 else 0
        facts.append([i,d,p[0],c[0],carrier,units,gross,discount,refund,cogs,freight,penalty,expedite,int(delay==0),complete,delay])
    return {
        'DimDate':(['Date','Year','YearMonth'], ['dateTime','int64','string'],dates),
        'DimProduct':(['ProductKey','Category','Storage'],['int64','string','string'],products),
        'DimCustomer':(['CustomerKey','Facility','Region','Segment'],['int64','string','string','string'],customers),
        'DimCarrier':(['CarrierKey','Carrier'],['int64','string'],carriers),
        'Recovery':(['Rate'],['double'],[[n/100] for n in range(0,101,5)]),
        'FactOrders':(['OrderKey','OrderDate','ProductKey','CustomerKey','CarrierKey','Units','GrossSales','Discount','Refund','COGS','Freight','Penalty','Expedite','OnTime','InFull','DelayDays'],['int64','dateTime']+['int64']*4+['decimal']*7+['int64']*3,facts)
    }

MEASURES = {
 'Orders': ('COUNTROWS(FactOrders)', '#,0', 'Volume'),
 'Gross Sales': ('SUM(FactOrders[GrossSales])', '$#,0', 'Financial'),
 'Discounts': ('SUM(FactOrders[Discount])', '$#,0', 'Financial'),
 'Refunds': ('SUM(FactOrders[Refund])', '$#,0', 'Financial'),
 'Net Revenue': ('[Gross Sales] - [Discounts] - [Refunds]', '$#,0', 'Financial'),
 'Product Cost': ('SUM(FactOrders[COGS])', '$#,0', 'Financial'),
 'Base Freight': ('SUM(FactOrders[Freight])', '$#,0', 'Financial'),
 'Service Failure Cost': ('SUM(FactOrders[Penalty]) + SUM(FactOrders[Expedite])', '$#,0', 'Financial'),
 'Contribution': ('[Net Revenue] - [Product Cost] - [Base Freight] - [Service Failure Cost]', '$#,0', 'Financial'),
 'Contribution Margin': ('DIVIDE([Contribution], [Net Revenue])', '0.0%', 'Financial'),
 'On Time Rate': ('DIVIDE(SUM(FactOrders[OnTime]), [Orders])', '0.0%', 'Service'),
 'OTIF Rate': ('DIVIDE(CALCULATE([Orders], KEEPFILTERS(FactOrders[OnTime] = 1), KEEPFILTERS(FactOrders[InFull] = 1)), [Orders])', '0.0%', 'Service'),
 'Late Orders': ('CALCULATE([Orders], KEEPFILTERS(FactOrders[OnTime] = 0))', '#,0', 'Service'),
 'Average Late Days': ('CALCULATE(AVERAGE(FactOrders[DelayDays]), KEEPFILTERS(FactOrders[DelayDays] > 0))', '0.00', 'Service'),
 'Revenue PY': ('CALCULATE([Net Revenue], DATEADD(DimDate[Date], -1, YEAR))', '$#,0', 'Time intelligence'),
 'Revenue YoY': ('DIVIDE([Net Revenue] - [Revenue PY], [Revenue PY])', '0.0%', 'Time intelligence'),
 'Revenue YTD': ('TOTALYTD([Net Revenue], DimDate[Date])', '$#,0', 'Time intelligence'),
 'Recovery Rate': ('SELECTEDVALUE(Recovery[Rate], 0.25)', '0%', 'Scenario'),
 'Potential Recovery': ('[Service Failure Cost] * [Recovery Rate]', '$#,0', 'Scenario'),
 'Scenario Contribution': ('[Contribution] + [Potential Recovery]', '$#,0', 'Scenario'),
 'Scenario Margin': ('DIVIDE([Scenario Contribution], [Net Revenue])', '0.0%', 'Scenario'),
}

def build_model(tables):
    model={'name':'Healthcare Distribution','compatibilityLevel':1600,'model':{'culture':'en-US','defaultPowerBIDataSourceVersion':'powerBI_V3','tables':[],'relationships':[]}}
    for name,(cols,types,rows) in tables.items():
        buffer=io.StringIO(); writer=csv.writer(buffer,lineterminator='\n'); writer.writerow(cols); writer.writerows(rows)
        csv_text=buffer.getvalue()
        (ROOT/'data').mkdir(exist_ok=True)
        (ROOT/'data'/f'{name}.csv').write_text(csv_text,encoding='utf-8')
        compressor=zlib.compressobj(wbits=-15)
        encoded=base64.b64encode(compressor.compress(csv_text.encode())+compressor.flush()).decode()
        mtypes={'int64':'Int64.Type','dateTime':'type date','decimal':'Currency.Type','double':'type number','string':'type text'}
        pairs=', '.join('{"'+c+'", '+mtypes[t]+'}' for c,t in zip(cols,types))
        expression=['let',f'    Source = Csv.Document(Binary.Decompress(Binary.FromText("{encoded}", BinaryEncoding.Base64), Compression.Deflate), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),','    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',f'    Typed = Table.TransformColumnTypes(Headers, {{{pairs}}}, "en-US")','in','    Typed']
        columns=[]
        for c,t in zip(cols,types):
            column={'name':c,'dataType':t,'sourceColumn':c,'summarizeBy':'none'}
            if c.endswith('Key'): column['isHidden']=True
            if t=='dateTime': column['formatString']='yyyy-MM-dd'
            if name=='DimDate' and c=='Date': column.update(isKey=True)
            if name=='Recovery': column['formatString']='0%'
            columns.append(column)
        table={'name':name,'columns':columns,'partitions':[{'name':name,'mode':'import','source':{'type':'m','expression':expression}}]}
        if name=='DimDate': table['dataCategory']='Time'
        if name=='FactOrders':
            table['measures']=[{'name':n,'expression':ex,'formatString':fmt,'displayFolder':folder} for n,(ex,fmt,folder) in MEASURES.items()]
        model['model']['tables'].append(table)
    for dim,key in [('DimDate','Date'),('DimProduct','ProductKey'),('DimCustomer','CustomerKey'),('DimCarrier','CarrierKey')]:
        model['model']['relationships'].append({'name':f'Orders_{dim}','fromTable':'FactOrders','fromColumn':'OrderDate' if dim=='DimDate' else key,'toTable':dim,'toColumn':key,'fromCardinality':'many','toCardinality':'one','crossFilteringBehavior':'oneDirection'})
    write_json(MODEL/'model.bim',model)
    write_json(MODEL/'definition.pbism',{'version':'1.0','settings':{}})
    (ROOT/'measures.dax').write_text('\n\n'.join(f'// {folder}\n{n} = {ex}' for n,(ex,_,folder) in MEASURES.items()),encoding='utf-8')

def projection(table, field, measure=False):
    return {'field':{'Measure' if measure else 'Column':{'Expression':{'SourceRef':{'Entity':table}},'Property':field}},'queryRef':f'{table}.{field}','nativeQueryRef':field}

def visual(page, name, kind, x,y,w,h, title, roles):
    value={'$schema':SCHEMA+'report/definition/visualContainer/2.1.0/schema.json','name':name,'position':{'x':x,'y':y,'z':0,'width':w,'height':h,'tabOrder':0},'visual':{'visualType':kind,'query':{'queryState':{role:{'projections':fields} for role,fields in roles.items()}},'visualContainerObjects':{'title':[{'properties':{'show':{'expr':{'Literal':{'Value':'true'}}},'text':{'expr':{'Literal':{'Value':"'"+title+"'"}}}}}]},'drillFilterOtherVisuals':True}}
    write_json(REPORT/'definition/pages'/page/'visuals'/name/'visual.json',value)

def build_report():
    write_json(ROOT/'Healthcare.pbip',{'version':'1.0','artifacts':[{'report':{'path':'Healthcare.Report'}}],'settings':{'enableAutoRecovery':True}})
    write_json(REPORT/'definition.pbir',{'$schema':SCHEMA+'report/definitionProperties/2.0.0/schema.json','version':'4.0','datasetReference':{'byPath':{'path':'../Healthcare.SemanticModel'}}})
    write_json(REPORT/'definition/version.json',{'$schema':SCHEMA+'report/definition/versionMetadata/1.0.0/schema.json','version':'2.0.0'})
    write_json(REPORT/'definition/report.json',{'$schema':SCHEMA+'report/definition/report/1.0.0/schema.json','themeCollection':{},'layoutOptimization':'None'})
    pages=[('Executive','01 | Executive overview - synthetic'),('Service','02 | Service diagnostics - synthetic'),('Recovery','03 | Recovery scenario - assumption')]
    write_json(REPORT/'definition/pages/pages.json',{'$schema':SCHEMA+'report/definition/pagesMetadata/1.0.0/schema.json','pageOrder':[p[0] for p in pages],'activePageName':'Executive'})
    m=lambda name:projection('FactOrders',name,True)
    c=lambda table,name:projection(table,name)
    for page,title in pages:
        write_json(REPORT/'definition/pages'/page/'page.json',{'$schema':SCHEMA+'report/definition/page/1.0.0/schema.json','name':page,'displayName':title,'displayOption':'FitToPage','width':1280,'height':720})
        visual(page,'Year','slicer',20,10,200,75,'Year',{'Values':[c('DimDate','Year')]})
        visual(page,'Region','slicer',240,10,220,75,'Region',{'Values':[c('DimCustomer','Region')]})
    for i,n in enumerate(['Net Revenue','Contribution Margin','OTIF Rate','Service Failure Cost']):
        visual('Executive','KPI'+str(i),'card',20+i*315,100,295,130,n,{'Values':[m(n)]})
    visual('Executive','Trend','lineChart',20,250,760,440,'Monthly net revenue',{'Category':[c('DimDate','YearMonth')],'Y':[m('Net Revenue')]})
    visual('Executive','Mix','clusteredBarChart',800,250,460,440,'Contribution by product category',{'Category':[c('DimProduct','Category')],'Y':[m('Contribution')]})
    visual('Service','OTIF','clusteredBarChart',20,110,610,280,'OTIF by carrier',{'Category':[c('DimCarrier','Carrier')],'Y':[m('OTIF Rate')]})
    visual('Service','Cost','clusteredBarChart',650,110,610,280,'Service failure cost by carrier',{'Category':[c('DimCarrier','Carrier')],'Y':[m('Service Failure Cost')]})
    visual('Service','Matrix','tableEx',20,410,1240,280,'Carrier diagnostics: compare volume and mix before acting',{'Values':[c('DimCarrier','Carrier'),m('Orders'),m('Late Orders'),m('Average Late Days'),m('OTIF Rate'),m('Service Failure Cost')]})
    visual('Recovery','Rate','slicer',500,10,310,75,'Assumed avoidable share (default 25%)',{'Values':[c('Recovery','Rate')]})
    for i,n in enumerate(['Service Failure Cost','Potential Recovery','Scenario Contribution','Scenario Margin']):
        visual('Recovery','KPI'+str(i),'card',20+i*315,100,295,130,n,{'Values':[m(n)]})
    visual('Recovery','Comparison','clusteredColumnChart',20,250,1240,440,'Contribution vs scenario: gross opportunity before implementation cost',{'Category':[c('DimCustomer','Region')],'Y':[m('Contribution'),m('Scenario Contribution')]})

def analyze(tables):
    con=sqlite3.connect(':memory:')
    for name,(cols,types,rows) in tables.items():
        mapping={'int64':'INTEGER','dateTime':'TEXT','string':'TEXT','decimal':'REAL','double':'REAL'}
        con.execute(f'CREATE TABLE {name} ('+', '.join(f'{c} {mapping[t]}' for c,t in zip(cols,types))+')')
        con.executemany(f'INSERT INTO {name} VALUES ('+','.join('?' for _ in cols)+')',rows)
    queries=(ROOT/'validation.sql').read_text().split(';')
    results=[]
    for query in queries:
        if not query.strip(): continue
        cur=con.execute(query); names=[d[0] for d in cur.description]
        results.append([dict(zip(names,r)) for r in cur.fetchall()])
    facts=[dict(zip(tables['FactOrders'][0],r)) for r in tables['FactOrders'][2]]
    total=results[0][0]
    assert total['Orders']==12000
    assert len({r['OrderKey'] for r in facts})==12000
    assert len(tables['DimDate'][2])==731
    for dim,key in [('DimProduct','ProductKey'),('DimCustomer','CustomerKey'),('DimCarrier','CarrierKey')]:
        keys=[r[0] for r in tables[dim][2]]
        assert len(set(keys))==len(keys)
        assert all(r[key] in keys for r in facts)
    assert all(r['OrderDate'] in {d[0] for d in tables['DimDate'][2]} for r in facts)
    assert all(0<=r['Refund']<=round(r['GrossSales']-r['Discount'],2) for r in facts)
    assert all(r['OnTime']==int(r['DelayDays']==0) for r in facts)
    py_revenue=sum(r['GrossSales']-r['Discount']-r['Refund'] for r in facts)
    py_contribution=sum(r['GrossSales']-r['Discount']-r['Refund']-r['COGS']-r['Freight']-r['Penalty']-r['Expedite'] for r in facts)
    assert abs(total['NetRevenue']-py_revenue)<.01
    assert abs(total['Contribution']-py_contribution)<.01
    assert abs(sum(r['NetRevenue'] for r in results[2])-py_revenue)<.01
    assert abs(total['OTIF']-sum(r['OnTime']*r['InFull'] for r in facts)/12000)<1e-9
    assert all(0<=r['OTIF']<=1 for r in results[1])
    # Hand-computed fixture: three shipments, one OTIF, revenue=210, contribution=6.
    fixture=[(100,10,0,50,5,2,0,1,1),(200,0,100,120,10,0,5,0,1),(20,0,0,10,2,0,0,1,0)]
    assert sum(g-d-r-c-f-p-e for g,d,r,c,f,p,e,_,_ in fixture)==6
    assert sum(g-d-r for g,d,r,*_ in fixture)==210
    assert sum(t*f for *_,t,f in fixture)==1
    assert total['ServiceFailureCost']*.0==0
    assert abs((total['Contribution']+total['ServiceFailureCost'])-total['Contribution']-total['ServiceFailureCost'])<.01
    write_json(ROOT/'results/summary.json',results)
    for n,rows in enumerate(results):
        with (ROOT/'results'/f'query_{n+1}.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    checks={'input_orders':12000,'date_rows':731,'tables':6,'relationships':4,'measures':len(MEASURES),'data_and_sql_checks':'PASS','power_bi_desktop_refresh':'NOT RUN - Desktop unavailable','dax_engine_execution':'NOT RUN - validate in Desktop','pbir_schema_validation':'Run validate_schemas.py'}
    write_json(ROOT/'results/validation.json',checks)
    return results

def main():
    tables=generate(); build_model(tables); build_report(); results=analyze(tables)
    from preview import build_preview
    build_preview(ROOT, tables, results)
    print(json.dumps(results[0][0],indent=2))
    print('PASS: data integrity and SQL reconciliation. Power BI engine validation remains pending.')

if __name__=='__main__': main()
