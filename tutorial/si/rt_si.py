##############################################################################
#
# Author: Alejandro Molina-Sanchez
# Run real-time simulations with yambo
# 
# Warning: Real-time simulations requires several data folders for running
# properly. Before using this scripts compulsively is recommended
# to understand the different run levels.
#
# Instructions: 
# The dictionary 'job' is a personal choice to store useful instructions. This
# is the serial version but one can add options for running in parallel and 
# any other thing. Feel free to play with it.
# calculation : 'collision', 'tdsex', 'negf', 'dissipation'
# folder-col  : collision data
# folder-run  : results (only work if collisions have been previously calculated)
# DG          : True or False if we use the double-grid (not yet implemented)
#
# Calculations are done inside the folder rt (feel free to rename it)
#
##############################################################################
#from __future__ import print_function
from yambopy import *
from qepy import *
import argparse
import os

# Select the run-level : 'collision', 'tdsex', 'pump', 'dissipation'
parser = argparse.ArgumentParser(description='Example of real-time simulation')
parser.add_argument('-c' ,'--collisions')
parser.add_argument('-t' ,'--tdsex')
parser.add_argument('-p' ,'--pump')
parser.add_argument('-d' ,'--dissipation')
args = parser.parse_args()

p2y      = 'p2y'
yambo    = 'yambo'
yambo_rt = 'yambo_rt'
ypp_rt   = 'ypp_rt'
ypp_ph   = 'ypp_ph'
folder   = 'rt'

job = dict()
job['folder-run']   = ''
job['folder-col']   = 'COLLISION'
job['folder-gkkp']  = 'GKKP'
job['DG']           = (False,'DG-60x60')

# check if the database is present
if not os.path.isdir('database'):
    os.mkdir('database')

#check if the nscf cycle is present
if os.path.isdir('nscf/si.save'):
    print('nscf calculation found!')
else:
    print('nscf calculation not found!')
    exit() 

#check if the SAVE folder is present
if not os.path.isdir('database/SAVE'):
    print('preparing yambo database')
    os.system('cd nscf/si.save; %s ;%s ; mv SAVE ../../database' % (p2y,yambo))

#check if the rt folder is present
if os.path.isdir('%s/SAVE'%folder):
  print('Symmetries for carrier dynamics ready') 
if not os.path.isdir('%s/SAVE'%folder):
  breaking_symmetries([1,0,0],folder=folder)

if args.collisions:
  print 'Collisions'  
  run = YamboIn('%s -r -e -v cohsex'%yambo_rt,folder=folder)
elif args.tdsex:
  print 'Time-dependent Screened-Exchange'  
  run = YamboIn('%s -q p'%yambo_rt,folder=folder)
elif args.pump:
  print 'Time-dependent with electric field'
  run = YamboIn('%s -q p'%yambo_rt,folder=folder)
elif args.dissipation:
  print 'Time-dependent with electric field and electron-phonon scattering'
  run = YamboIn('%s -s p -q p'%yambo_rt,folder=folder)
else:
  print 'Invalid calculation type'
  exit()

# System Common variables NOW ARE THEY ONLY IN THE COLLISIONS?
#run['FFTGvecs']  = [5,'Ha']
#run['HARRLvcs']  = [5,'Ha'] # New Variable, ask DS
#run['EXXRLvcs']  = [100,'mHa']  # Why must EXXRLvcs <= NGsBlkXs

# Collision variables
if args.collisions:
  run['FFTGvecs']  = [5,'Ha']
  run['HARRLvcs']  = [5,'Ha'] # New Variable, ask DS
  run['EXXRLvcs']  = [100,'mHa']  # Why must EXXRLvcs <= NGsBlkXs
  run['NGsBlkXs']  = [ 100,'mHa']
  run['BndsRnXs' ] = [1,30]
  run['COLLBands'] = [2,7]     # Bug in the Initizalization. Tell DS
  run.write('%s/03_COLLISION'%folder)

# Common time-dependent variable
if args.tdsex or args.pump or args.dissipation:
  run['RTBands']    = [2,7]
  run['GfnQP_Wv']   = [0.10,0.00,0.00]
  run['GfnQP_Wc']   = [0.10,0.00,0.00]
  run['GfnQPdb']    = 'none' 
  run['Potential']  = 'COHSEX' 
  # Time-propagation 
  run['RTstep']     = [  10.0,'as']
  run['NETime']     = [   2.0,'ps']
  run['Integrator'] = "RK2 RWA"
  run['IOtime']     = [ [1.000, 1.000, 1.000], 'fs' ] 
  # Pump Pulse
  run['Field1_Int']       = [ 1E5 , 'kWLm2']    # Intensity pulse
  run['Field1_Dir']       = [1.0,0.0,0.0]  # Polarization pulse
  run['Field1_Dir_circ']  = [0.0,1.0,0.0]  # Polarization pulse
  run['Field1_pol']       = "linear"            # Polarization type (linear or circular) 

# Time-dependent COHSEX -- DELTA PULSE
if args.tdsex:
  run['Field1_kind'] = "DELTA"
  run.write('%s/04_TDSEX'%folder)

# Pumping with finite pulse
if args.pump or args.dissipation:
  run['Field1_kind'] = "QSSIN"
  run['Field1_Damp'] = [ 100,'fs']
  run['Field1_Freq'] = [[2.1,0.0],'eV']

if args.pump:
  run.write('%s/05_NEGF'%folder)

# Pumping with finite pulse and electron-phonon dissipation
if args.pump or args.dissipation:
# Interpolation 
  run['LifeInterpKIND']  = 'FLAT'
  run['LifeInterpSteps'] = [ [1.0,1.0], 'fs' ] 
  run.write('%s/06_DISS'%folder)

# Submission in serial

# Collisions

if args.collisions:
  print('running yambo-collision')
  os.system('cd %s; %s -F 03_COLLISION -J %s'%(folder,yambo_rt,job['folder-col']))

# Time-dependent without/with Double Grid 

if args.tdsex:
  job['folder-run'] += 'tdsex'
  print('running TD-COHSEX in folder: ' + str(job['folder-run']))
  if not os.path.isdir('%s/'%folder+job['folder-col']):
    print 'Collisions not found'
    exit()
  if job['DG'][0]:
    print('with Double Grid from folder %s'%job['DG'][1])
    os.system('cd %s; %s -F 04_TDSEX -J \'%s,%s,%s\' -C %s'%(folder,yambo_rt,job['folder-run'],job['folder-col'],job['DG'][1],job['folder-run']))
  else:
    os.system ('cd %s; %s -F 04_TDSEX -J \'%s,%s\' -C %s'%(folder,yambo_rt,job['folder-run'],job['folder-col'],job['folder-run']))

# Time-dependent with a pulse and without/with Double Grid 

if args.pump:
  print('running pumping with finite pulse')
  job['folder-run'] += 'negf'
  print('running NEGF in folder: ' + str(job['folder-run']))
  if not os.path.isdir('%s/'%folder+job['folder-col']):
    print 'Collisions not found'
    exit()
  if job['DG'][0]:
    print('with Double Grid from folder %s'%job['DG'][1])
  else:
    #os.system ('cd %s; %s -F 05_NEGF -J \'%s,%s\' -C %s'%(folder,yambo_rt,job['folder-run'],job['folder-col'],job['folder-run']))
    print 'cd %s ; %s -F 05_NEGF -J \'%s,%s\' -C %s'%(folder,yambo_rt,job['folder-run'],job['folder-col'],job['folder-run'])

# Time-dependent with a pulse and dissipation and without/with Double Grid 

if args.dissipation:
  print('running pumping with finite pulse and with electron-phonon scattering')
  print('this run level needs the GKKP folder to run')
  job['folder-run'] += 'dneq'
  if not os.path.isdir('%s/'%folder+job['folder-col']):
    print 'Collisions not found'
    exit()
  if os.path.isdir('%s/GKKP'%folder):
    print('Gkkp files exists')
    if job['DG'][0]:
      print('with Double Grid from folder %s'%job['DG'][1])
      print('%s -F 06_DISS -J \'%s,%s,%s\''%(yambo_rt,job['folder-run'],job['folder-col'],job['DG'][1]))
    else:
      os.system ('cd %s; %s -F 06_DISS -J \'%s,%s,%s\' -C %s'%(folder,yambo_rt,job['folder-run'],job['folder-col'],job['folder-gkkp'],job['folder-run']))
      print 'cd %s; %s -F 06_DISS -J \'%s,%s,%s\' -C %s'%(folder,yambo_rt,job['folder-run'],job['folder-col'],job['folder-gkkp'],job['folder-run'])
  else:
    print('No gkkp files. Calculation stop')
    print('You may run gkkp_si.py')
    exit()
