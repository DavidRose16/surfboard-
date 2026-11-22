import sys, numpy as np, json
from OCP.STEPControl import STEPControl_Reader
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE
from OCP.TopoDS import TopoDS
from OCP.BRep import BRep_Tool
r=STEPControl_Reader(); r.ReadFile(sys.argv[1]); r.TransferRoots(); s=r.OneShape()
e=TopExp_Explorer(s,TopAbs_FACE); f=TopoDS.Face(e.Current()); S=BRep_Tool.Surface_s(f)
us=np.linspace(0,1,1201); rows=[]
vs=np.unique(np.concatenate([np.linspace(0,1,1500),np.linspace(0,0.03,200),np.linspace(0.97,1,200)]))
for v in vs:
    P=np.array([(lambda p:(p.X(),p.Y(),p.Z()))(S.Value(u,v)) for u in us])
    i=np.argmax(P[:,1]); j=np.argmin(P[:,1])
    # refine
    def best(i,sign):
        lo,hi=us[max(i-1,0)],us[min(i+1,len(us)-1)]
        uu=np.linspace(lo,hi,41); Q=np.array([(lambda p:(p.X(),p.Y(),p.Z()))(S.Value(u,v)) for u in uu])
        k=np.argmax(sign*Q[:,1]); return Q[k]
    a=best(i,1); b=best(j,-1)
    rows.append([v,*a,*b, P[:,0].min(),P[:,0].max()])
np.save(sys.argv[2],np.array(rows)); R=np.array(rows)
print("x spread within section max:",(R[:,8]-R[:,7]).max())
print("sym max diff", np.abs(R[:,2]+R[:,5]).max())
