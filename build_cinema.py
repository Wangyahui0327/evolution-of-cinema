import pandas as pd,json,os,collections
root='/mnt/data/cinema_evolution_dashboard'; dat=root+'/data'
read=lambda f:pd.read_csv('/mnt/data/'+f+'(1).xls',low_memory=False)
m=read('movies');g=read('movie_genres');cast=read('movie_cast');crew=read('movie_crew');aw=read('movie_awards')
print('roles',crew.role.value_counts().head(15).to_dict());print('outcome',aw.outcome.value_counts().head().to_dict())
gm=g.dropna(subset=['genre']).groupby('film_id').genre.apply(lambda s:sorted(set(s.astype(str)))).to_dict()
# high-level normalization: explicit source names kept and noise excluded in UI by limiting top 10
def tok(s):return [v.strip() for v in str(s).split('|') if v.strip() and v.strip()!='nan'] if pd.notna(s) else []
rows=[]
for r in m.itertuples(index=False):
 yr=int(r.release_year) if pd.notna(r.release_year) and 1880<=r.release_year<=2030 else None
 rv=lambda x:round(float(x),2) if pd.notna(x) else None
 rows.append({'id':str(r.film_id),'title':str(r.title),'year':yr,'countries':tok(r.countries),'genres':gm.get(str(r.film_id),tok(r.genres)),'rt':rv(r.rotten_tomatoes_pct),'mc':rv(r.metacritic_score),'budget':rv(r.budget_usd) if pd.notna(r.budget_usd) and r.budget_usd>0 else None,'revenue':rv(r.box_office_usd) if pd.notna(r.box_office_usd) and r.box_office_usd>0 else None})
with open(dat+'/movies.json','w',encoding='utf8') as f:json.dump(rows,f,ensure_ascii=False,separators=(',',':'))
# actor/director collaboration edges per film, limit cast top 6 if ordered else first 6, director by crew role
print('country example',rows[0]['countries'])
film_year={r['id']:r['year'] for r in rows}
roles=crew[crew.role.str.lower().eq('director')].dropna(subset=['person_id']).drop_duplicates(['film_id','person_id'])
actors=cast.sort_values('cast_order',na_position='last').drop_duplicates(['film_id','person_id']).groupby('film_id').head(6)
# Vectorized director-actor connections
pairs=roles[['film_id','person_id','person']].merge(actors[['film_id','person_id','person']],on='film_id',suffixes=('_d','_a'))
pairs=pairs[pairs.person_id_d.ne(pairs.person_id_a)].copy()
pairs['year']=pairs.film_id.map(film_year)
pairs=pairs.dropna(subset=['year','person_d','person_a'])
pairs['decade']=(pairs.year.astype(int)//10)*10
pairs=pairs.drop_duplicates(['film_id','person_id_d','person_id_a'])
agg=pairs.groupby(['decade','person_id_d','person_id_a','person_d','person_a'],as_index=False).size()
counts={};names={}
for row in agg.itertuples(index=False):
 counts[(row.decade,str(row.person_id_d),str(row.person_id_a))]=int(row.size)
 names[str(row.person_id_d)]=str(row.person_d);names[str(row.person_id_a)]=str(row.person_a)
# only pairs recurring twice+, include top overall per decade and examples to enable exploration
edges=[]
for (dec,di,ai),count in counts.items():
 if count>=2:edges.append({'decade':dec,'source':di,'target':ai,'director':names[di],'actor':names[ai],'films':count})
edges=sorted(edges,key=lambda x:(-x['films'],x['director'],x['actor']))
with open(dat+'/collaborations.json','w',encoding='utf8') as f:json.dump(edges,f,ensure_ascii=False,separators=(',',':'))
meta={'movies':len(rows),'genre_rows':len(g),'crew_rows':len(crew),'cast_rows':len(cast),'awards_rows':len(aw),'rated_rt':sum(r['rt'] is not None for r in rows),'edges':len(edges),'network_definition':'Director–actor pairs appearing in at least two films released in the same decade; up to six cast members per film, sorted by cast_order where available. No claim about production relationships beyond credited co-appearance.'}
with open(dat+'/metadata.json','w') as f:json.dump(meta,f,indent=2)
print(meta, 'size MB',os.path.getsize(dat+'/movies.json')/1e6)
