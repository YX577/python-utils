### Import useful routines
import numpy as np
import string
import glob
import os
from collections import Counter

### Import CDAT routines ###
import MV2 as MV
import cdms2 as cdms
import genutil
import cdutil
import cdtime
from eofs.cdms import Eof

### Import scipy routines for smoothing, interpolation
from scipy.interpolate import interp1d
from scipy.optimize import brentq,fminbound
import scipy.ndimage as ndimag

### Import plotting routines
import matplotlib.pyplot as plt
#from mpl_toolkits.basemap import Basemap  
import matplotlib.cm as cm
from mpl_toolkits.axes_grid1 import make_axes_locatable

import CMIP5_tools as cmip5

import matplotlib.mlab as mlab

### Set classic Netcdf (ver 3)
cdms.setNetcdfShuffleFlag(0)
cdms.setNetcdfDeflateFlag(0)
cdms.setNetcdfDeflateLevelFlag(0)

def concatenate_this(piC,modaxis=0,compressed=False):
    if not ("time" in piC.getAxisIds()):
        print("Need a time axis to concatenate along")
        raise TypeError

   
        
   
    if compressed:
        axlist = piC.getAxisList()
        todel=[]

        modax = piC.getAxis(modaxis)
        allfiles=eval(modax.models)
        if len(allfiles)!=piC.shape[modaxis]:
            allfiles =[x+".xml" for x in allfiles[0].split(".xml")[:-1]]
        
        allfiles=np.array(allfiles)
        #assume model axis is 0 for this
        for i in range(len(allfiles)):
            if len(piC[i].compressed()) != len(piC[i]):
                todel+=[i]
        piC = MV.array(np.delete(piC,todel,axis=modaxis))
        allfiles = np.delete(allfiles,todel).tolist()
        newmodax=cmip5.make_model_axis(allfiles)
        piC.setAxisList([newmodax]+axlist[1:])
                
                
    naxes = len(piC.shape)
    
    timeaxis = piC.getAxisIds().index("time")
    dimensions=piC.shape
    nmodc = dimensions[modaxis]

    ntc = dimensions[timeaxis]
            
    newdim = (nmodc*ntc,)

    units = 'days since 0001-1-1'
    start = cdtime.comptime(1,1,1)
    tax = cdms.createAxis(np.arange(0,nmodc*ntc*365,365)+15.5)
    #tax = cdms.createAxis([start.add(i,cdtime.Months).torel(units).value for i in range(ntc*nmodc)])
    tax.units = units
    tax.id = "time"
    tax.designateTime()
    newaxes = [tax]
    if len(dimensions)>2:
       
        for i in range(len(dimensions)):
            if (i != timeaxis) and (i!= modaxis):
    
                newdim+=(dimensions[i],)
                newaxes+=[piC.getAxis(i)]
    
    piC_concatenate = piC.reshape(newdim)

    
    piC_concatenate.setAxisList(newaxes)
    
    return piC_concatenate

def get_slopes(c,yrs,plot = False):
    """
    get non-overlapping trends in concatenated control run
    """
    trends = np.ma.array([])
    start = 0
    end = yrs
    if plot:
        
        Ntot = float(len(c)/yrs)
    while end < len(c):
        ctrunc = c[start:end]
        #if len(ctrunc.compressed()) == len(ctrunc):
        if True:
        # Express in "per decade" units.  All control runs are in days.
            slope0,intercept0 = genutil.statistics.linearregression(ctrunc)
            slope = slope0*3650.
            if plot:
                xax = cmip5.get_plottable_time(ctrunc)
                plt.plot(xax,ctrunc.asma(),color = cm.RdYlBu(float(start/yrs)/Ntot))
                plt.plot(xax,float(slope0)*ctrunc.getTime()[:]+float(intercept0),color ="k",linewidth = 3)
            trends = np.append(trends,slope)
        start = end
        end += yrs
       
    trends = MV.masked_where(np.isnan(trends),trends)
    trends = trends.compressed()
    return trends


def get_orientation(solver):
    pc1 = solver.pcs()[:,0]
    fac = float(np.sign(genutil.statistics.linearregression(pc1,nointercept=1)))
    return fac

def fit_normals_to_data(C,**kwargs):
    a = kwargs.pop("a",None)
    ax = kwargs.pop("ax",None)
    if ax is None:
        ax=plt.gca()
    if a is None:
        a = np.max(np.abs(C))
        a = a + 0.5*a
    delta = a/25.
    xc = np.arange(-a,a+delta,delta)

    muc = np.ma.average(C)
    sigc = np.ma.std(C)
    fac = 1./sigc
    pdfc = mlab.normpdf(xc,muc,sigc)
    ax.plot(xc,pdfc,**kwargs)
