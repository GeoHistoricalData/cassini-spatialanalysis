# coding: utf8
import argparse
import sys
from igraph import *
from  psycopg2 import *
import shapefile
import logging
from scipy.spatial import Voronoi
from argparse import RawTextHelpFormatter

'''GLOBALS'''
CON_STR = "port=5432 host=geohistoricaldata.org dbname=ghdb user=ghdb_read_only password=ghdb_read_only"
ALPHA = 500.0 #Default value of the disyance threshold
BBOX52 = 'SRID=2154;MULTIPOLYGON(((764888.786132299 6492879.32317303,687116.995262039 6493785.37890199,687553.636039631 6543122.02721408,765542.471445634 6542310.77705176,764888.786132299 6492879.32317303)))'
METHODS=['full', 'parishes', 'settlement', 'religion']



def genFullGraph(threshold):
  logging.debug("""
  ------------------------------------------------------\n
  Full graph generation with  t="""+str(threshold)+"""m'\n
  Based on: topo:* (except 'Autre')
  ------------------------------------------------------
  """)  
  logging.debug('Connecting to db...')
  conn = connect(CON_STR)
  cur = conn.cursor()
  query = """
        DROP TABLE IF EXISTS nodes;
        CREATE TEMP TABLE nodes(
          gid integer,
          id integer,
          geom geometry,
          tbl varchar(20)
        );

        CREATE INDEX nodes_gist
          ON nodes
          USING gist
          (geom);
          
        INSERT INTO nodes 
        SELECT row_number() OVER () AS gid, * FROM 
        (
          SELECT id, geom, 'toponym' as tbl
                FROM france_cassini_toponyms
                WHERE ST_WITHIN(geom, St_GeomFromEWKT('"""+BBOX52+"""'))
                AND type_id != 28 --Don't take toponyms of type 'autre'
                AND type_id !=  1 -- Don't keep 'clochers' because they are already registered as 'chefs lieux'
                UNION
                SELECT gid as id, geom, 'cheflieu'  as tbl
                FROM france_cassini_chefs_lieux
                WHERE ST_WITHIN(geom, St_GeomFromEWKT('"""+BBOX52+"""'))
        ) as merge;

      SELECT a.id AS id_a, ST_X(a.geom) as x_a, ST_Y(a.geom) as y_a, b.id AS id_b, ST_X(b.geom) as x_b, ST_Y(b.geom) as y_b, ST_DISTANCE(a.geom,b.geom) as d2 FROM 
      (
        SELECT * FROM nodes
      ) AS a
      CROSS JOIN LATERAL 
      (
        SELECT * FROM nodes
        WHERE id != a.id
        AND ST_DWITHIN(a.geom,geom,"""+str(threshold)+""")
      ) AS b
  """
  logging.debug('Fetching data...')
  cur.execute(query)

  g = Graph()
  for r in g.es:
    print(r)
  #Populate nodes
  logging.debug('Populating the graph...')
  edges = []
  vertices = set()
  vpos = []
  weights = []
  for tn in cur.fetchall():
    n1 = str(tn[0])
    n2 = str(tn[3])
    e = set([n1,n2])
    if not e in edges:
      edges.append(e)
      weights.append(tn[6])
      vertices.add((n1,(tn[1],tn[2])))
      vertices.add((n2,(tn[4],tn[5])))

  [g.add_vertex(name=v[0],loc=v[1]) for v in vertices]
  g.add_edges([list(e) for e in edges])
  del conn #Connexion can now be closed

  logging.debug('Computing minimum spanning tree...')
  g = g.spanning_tree(weights)

  logging.debug('Computing connected components...')
  clusters = g.clusters(mode=WEAK)

  logging.debug('Outputting connected components to shapefile...')
  wcc = shapefile.Writer()
  wcc.field("component")
  for cid, c in enumerate(clusters.subgraphs()):
    mline = []
    for e in c.es:
      v = c.vs[e.tuple[0]]
      vv = c.vs[e.tuple[1]]
      line = [list(v["loc"]),list(vv["loc"])]
      mline.append(line)
    wcc.line(parts=mline)
    wcc.record(cid)
  wcc.save('./output/full')


def genSettlementAreas(threshold):
  logging.debug("""
    ------------------------------------------------------\n
    Graph of the settlement areas with t="""+str(threshold)+"""m'\n
    Based on: cl:*, topo:hameau, topo:château, topo:maison\n
    , topo:gentilhommiere\n
    ------------------------------------------------------
    """)  
  logging.debug('Connecting to db...')
  conn = connect(CON_STR)
  cur = conn.cursor()
  query = """
        DROP TABLE IF EXISTS nodes;
        CREATE TEMP TABLE nodes(
          gid integer,
          id integer,
          geom geometry,
          tbl varchar(20)
        );

        CREATE INDEX nodes_gist
          ON nodes
          USING gist
          (geom);
          
        INSERT INTO nodes 
        SELECT row_number() OVER () AS gid, * FROM 
        (
          SELECT id, geom, 'toponym' as tbl
                FROM france_cassini_toponyms
                WHERE ST_WITHIN(geom, St_GeomFromEWKT('"""+BBOX52+"""'))
                AND (type_id = 10 OR  type_id = 11 OR  type_id = 12 OR type_id = 13) --inhabited places
                UNION
                SELECT gid as id, geom, 'cheflieu'  as tbl
                FROM france_cassini_chefs_lieux
                WHERE ST_WITHIN(geom, St_GeomFromEWKT('"""+BBOX52+"""'))
        ) as merge;

      SELECT a.id AS id_a, ST_X(a.geom) as x_a, ST_Y(a.geom) as y_a, b.id AS id_b, ST_X(b.geom) as x_b, ST_Y(b.geom) as y_b, ST_DISTANCE(a.geom,b.geom) as d2 FROM 
      (
        SELECT * FROM nodes
      ) AS a
      CROSS JOIN LATERAL 
      (
        SELECT * FROM nodes
        WHERE id != a.id
        AND ST_DWITHIN(a.geom,geom,"""+str(threshold)+""")
      ) AS b
  """
  logging.debug('Fetching data...')
  cur.execute(query)

  g = Graph()
  for r in g.es:
    print(r)
  #Populate nodes
  logging.debug('Populating the graph...')
  edges = []
  vertices = set()
  vpos = []
  weights = []
  for tn in cur.fetchall():
    n1 = str(tn[0])
    n2 = str(tn[3])
    e = set([n1,n2])
    if not e in edges:
      edges.append(e)
      weights.append(tn[6])
      vertices.add((n1,(tn[1],tn[2])))
      vertices.add((n2,(tn[4],tn[5])))

  [g.add_vertex(name=v[0],loc=v[1]) for v in vertices]
  g.add_edges([list(e) for e in edges])
  del conn #Connexion can now be closed

  logging.debug('Computing minimum spanning tree...')
  g = g.spanning_tree(weights)

  logging.debug('Computing connected components...')
  clusters = g.clusters(mode=WEAK)

  logging.debug('Outputting connected components to shapefile...')
  wcc = shapefile.Writer()
  wcc.field("component")
  for cid, c in enumerate(clusters.subgraphs()):
    mline = []
    for e in c.es:
      v = c.vs[e.tuple[0]]
      vv = c.vs[e.tuple[1]]
      line = [list(v["loc"]),list(vv["loc"])]
      mline.append(line)
    wcc.line(parts=mline)
    wcc.record(cid)
  wcc.save('./output/settlement')


def genChurchAreas(threshold):
  logging.debug("""
    ------------------------------------------------------\n
    Graph of the church areas with t="""+str(threshold)+"""m'\n
    Based on: cl:abbaye, cl:prieuré, topo:chapelle,\n
    topo:calvaire, topo:cimetiere, topo:Autre lieu religieux\n
    ------------------------------------------------------
    """)
  logging.debug('Connecting to db...')
  conn = connect(CON_STR)
  cur = conn.cursor()
  query = """
        DROP TABLE IF EXISTS nodes;
        CREATE TEMP TABLE nodes(
          gid integer,
          id integer,
          geom geometry,
          tbl varchar(20)
        );

        CREATE INDEX nodes_gist
          ON nodes
          USING gist
          (geom);
          
        INSERT INTO nodes 
        SELECT row_number() OVER () AS gid, * FROM 
        (
          SELECT id, geom, 'toponym' as tbl
                FROM france_cassini_toponyms
                WHERE ST_WITHIN(geom, St_GeomFromEWKT('"""+BBOX52+"""'))
                AND (type_id = 6 OR  type_id = 7 OR  type_id = 9 OR type_id = 3 OR type_id = 5) --Places related to religion
                UNION
                SELECT gid as id, geom, 'cheflieu'  as tbl
                FROM france_cassini_chefs_lieux
                WHERE ST_WITHIN(geom, St_GeomFromEWKT('"""+BBOX52+"""'))
                AND typecart LIKE 'abbaye' OR typecart LIKE 'prieuré' 
        ) as merge;

      SELECT a.id AS id_a, ST_X(a.geom) as x_a, ST_Y(a.geom) as y_a, b.id AS id_b, ST_X(b.geom) as x_b, ST_Y(b.geom) as y_b, ST_DISTANCE(a.geom,b.geom) as d2 FROM 
      (
        SELECT * FROM nodes
      ) AS a
      CROSS JOIN LATERAL 
      (
        SELECT * FROM nodes
        WHERE id != a.id
        AND ST_DWITHIN(a.geom,geom,"""+str(threshold)+""")
      ) AS b
  """
  logging.debug('Fetching data...')
  cur.execute(query)

  g = Graph()
  for r in g.es:
    print(r)
  #Populate nodes
  logging.debug('Populating the graph...')
  edges = []
  vertices = set()
  vpos = []
  weights = []
  for tn in cur.fetchall():
    n1 = str(tn[0])
    n2 = str(tn[3])
    e = set([n1,n2])
    if not e in edges:
      edges.append(e)
      weights.append(tn[6])
      vertices.add((n1,(tn[1],tn[2])))
      vertices.add((n2,(tn[4],tn[5])))

  [g.add_vertex(name=v[0],loc=v[1]) for v in vertices]
  g.add_edges([list(e) for e in edges])
  del conn #Connexion can now be closed

  logging.debug('Computing minimum spanning tree...')
  g = g.spanning_tree(weights)

  logging.debug('Computing connected components...')
  clusters = g.clusters(mode=WEAK)

  logging.debug('Outputting connected components to shapefile...')
  wcc = shapefile.Writer()
  wcc.field("component")
  for cid, c in enumerate(clusters.subgraphs()):
    mline = []
    for e in c.es:
      v = c.vs[e.tuple[0]]
      vv = c.vs[e.tuple[1]]
      line = [list(v["loc"]),list(vv["loc"])]
      mline.append(line)
    wcc.line(parts=mline)
    wcc.record(cid)
  wcc.save('./output/religion')


def genParishSpiders():
  logging.debug("""
  ------------------------------------------------------\n
  Parishes/succursal voronoi-based graphs'\n
  ------------------------------------------------------
  """)  
  logging.debug('Connecting to db...')
  conn = connect(CON_STR)
  cur = conn.cursor()
  query = """
    WITH RECURSIVE cluster AS (
    SELECT ST_X(a.geom) AS x_a,ST_Y(a.geom) AS y_a, b.gid as cellid, px ,py FROM 
    (
    SELECT * FROM france_cassini_toponyms 
    WHERE type_id = 10 --Keep only hamlets
    ) a
    ,
    (
    SELECT x.gid,ST_INTERSECTION(x.geom,St_GeomFromEWKT('"""+BBOX52+"""')) AS geom, ST_X(y.geom) as px, ST_Y(y.geom) as py FROM travail.voronoi_parishes_52 AS x JOIN france_cassini_chefs_lieux AS y ON x.gid = y.gid
    ) b
    WHERE ST_WITHIN(a.geom,b.geom)
    )
    SELECT * FROM cluster ORDER BY cellid;
  """
  cur.execute(query)
  wcc = shapefile.Writer()
  wcc.field("cell")
  for tn in cur.fetchall():
    line = [[[tn[0],tn[1]],[tn[3],tn[4]]]]
    wcc.line(parts=line)
    wcc.record(tn[2])
  wcc.save('./output/parishes')

def check_positive(f):
  try:
    float(f)
  except ValueError:
    raise argparse.ArgumentTypeError("Threshold must be a number.")
  if float(f) <= 0.0:
    raise argparse.ArgumentTypeError("Threshold must be a positive number.")
  return f

def check_method(m):
  if m not in  METHODS:
    raise argparse.ArgumentTypeError("Invalid method: %s. Available methods are." % str(m),METHODS)
  return m


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Generate graphs on the Cassini map sheet n° 52.')
  parser.add_argument('-d','--debug', action='store_true', help='Activates debug mode.')
  parser.add_argument('-t','--threshold', type=check_positive, nargs='?',help='A distance threshold used in some methods.') #No default value then no unexpected results :-)
  required = parser.add_argument_group('required arguments')
  required.add_argument('-m','--method',required=True, type=check_method, nargs='+',help='One or several methods to be executed, among '+str(METHODS)+'. Use spaces as separators to execute several methods.\n Example: \'gen.py -t 800.0 -m parishes full\'')
  try:
    args = parser.parse_args(sys.argv[1:])
  except Exception as e: 
    parser.print_help()
    print(e)
    sys.exit(1)

  if args.threshold is None and (args.method not in [m for m in METHODS if m !='parishes']):
      parser.error("One of the method to execute requires a distance threshold (-t X or --threshold X).")
  if args.debug:
    logging.basicConfig(level=logging.DEBUG, format='%(relativeCreated)6d %(threadName)s %(message)s')

  logging.debug('Using threshold = '+str(args.threshold))
  for m in args.method:
    if m == 'full':
      genFullGraph(args.threshold)
    if m == 'settlement':
      genSettlementAreas(args.threshold)
    if m == 'religion':
      genChurchAreas(args.threshold)
    if m == 'parishes':
      genParishSpiders()
