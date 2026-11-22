import sys, json
from OCP.STEPControl import STEPControl_Reader
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE, TopAbs_VERTEX
from OCP.TopoDS import TopoDS
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Plane, GeomAbs_Cylinder
r=STEPControl_Reader(); r.ReadFile(sys.argv[1]); r.TransferRoots(); s=r.OneShape()
e=TopExp_Explorer(s,TopAbs_FACE); fins=[]; leash=None
while e.More():
    f=TopoDS.Face(e.Current()); a=BRepAdaptor_Surface(f)
    v=TopExp_Explorer(f,TopAbs_VERTEX); P=set()
    while v.More():
        p=BRep_Tool.Pnt_s(TopoDS.Vertex(v.Current())); P.add((round(p.X(),3),round(p.Y(),3),round(p.Z(),3))); v.Next()
    P=sorted(P)
    if a.GetType()==GeomAbs_Plane and len(P)==4:
        xs=[p[0] for p in P]; zs=[p[2] for p in P]
        if max(zs)-min(zs)<1e-3 and max(xs)-min(xs)>80: fins.append([[p[0]/25.4,p[1]/25.4] for p in P])
    if a.GetType()==GeomAbs_Cylinder:
        c=a.Cylinder(); l=c.Location(); leash={"x":l.X()/25.4,"y":l.Y()/25.4,"r":c.Radius()/25.4}
    e.Next()
json.dump({"fins":fins,"leash":leash},open(sys.argv[2],"w"),indent=1); print(json.dumps({"fins":fins,"leash":leash}))
