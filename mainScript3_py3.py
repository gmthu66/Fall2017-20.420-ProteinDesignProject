#!/usr/local/bin python3.6
# mainScript3_py3.py

import os
import subprocess
import re
import random
import pprint
from datetime import datetime
import itertools

from pyrosetta import *
from pyrosetta.toolbox import generate_resfile_from_pose
from pyrosetta.rosetta.protocols.simple_moves import *
from pyrosetta.rosetta.protocols.relax import FastRelax
from pyrosetta.rosetta.protocols.moves import AddPyMOLObserver
from pyrosetta.rosetta.core.pack.task import TaskFactory
from pyrosetta.rosetta.core.pack.task import parse_resfile
from reference_utils import funmap, parmap


def madeGlobal(varName):
    return varName in globals()

def now(formatNum=0):
    if formatNum == 0:
        return datetime.now().strftime('%H:%M:%S %m-%d-%y')
    elif formatNum == 1:
        return datetime.now().strftime('%y%m%d')
    elif formatNum == 2:
        return datetime.now().strftime('%H:%M:%S')
    elif formatNum == 3:
        return datetime.now().strftime('%d%H%M%S')

def mkDir(directory):
    if not os.path.isdir(directory):
        os.makedirs(directory)

def isFile(fileName):
    return os.path.isfile(fileName)

def initialize():
    if not madeGlobal('didInit'):
        init()
        global didInit, defaultScorefxn, proteinName
        proteinName = '3vi8_BPDE'
        didInit = True
        defaultScorefxn = get_fa_scorefxn()
initialize()

def setupCaches():
    if not madeGlobal('cacheDir'):
        global cacheDir
        cacheDir = 'AlgorithmCache'
    mkDir(cacheDir)

    if not madeGlobal('pdbCache'):
        global pdbCache
        pdbCache = os.path.join(cacheDir,'PDBs')
    mkDir(pdbCache)

    global dec_dir
    
    global sesCache
    if madeGlobal('sesCache'):
        if now(1) in sesCache:
            return
    sesCache = '{}_session_log.txt'.format(now(1))
    sesCache = os.path.join(cacheDir,sesCache)
    if not isFile(sesCache):
        with open(sesCache,'w') as f:
            f.writelines('{}\n\n'.format(sesCache))
            f.writelines(('Protein Design Algorithm Trials, '
                          'Session Log\nBegins: {}\n\n').format(now()))


setupCaches()


# FIXME - Integrate into ResfileBuilder Class
def make_sequence_globals():
    if madeGlobal('madeSeqGlobals'):
            return
    global pocketResNums, firstResNum, lastResNum,  oneIndexedRes, scoreDict,\
        allAa, aaGroupings, adnlAa, conservMutMap, liberalMutMap, madeSeqGlobals
    
    pocketResNums = [241, 247, 250, 251, 254, 255, 272, 273, 275, 276, 279, 280,
                     321, 325, 330, 332, 333, 334, 339, 343, 344, 354, 355, 358]
    firstResNum = 202
    lastResNum = 468
    oneIndexedRes = [i - firstResNum + 1 for i in pocketResNums]
    allAa = ['A','C','D','E','F','G','H','I','K','L',
             'M','N','P','Q','R','S','T','V','W','Y']
    print(len(allAa))
    aaGroupings = [['A','I','L','M','V'],
                   ['F','W','Y'],
                   ['N','C','Q','T','S'],
                   ['D','E'],
                   ['R','H','K'],
                   ['G'],
                   ['P']]
    adnlAa = [['F','W','Y','G'],
              ['A','I','L','M','V','G'],
              ['Y','W','G'],
              ['R','H','K','G'],
              ['D','E','G'],
              ['A','S'],
              ['G']]
    conservMutMap = {}
    liberalMutMap = {}
    for i,aaList in enumerate(aaGroupings):
        for j,aa in enumerate(aaList):
            temp_list = list(aaList)
            del temp_list[j]
            conservMutMap[aa] = temp_list
            liberalMutMap[aa] = temp_list + adnlAa[i]
    scoreDict = {}
    madeSeqGlobals = True
make_sequence_globals()


def log(text='', no_stamp=False):
    with open(sesCache,'a') as f:
        for line in text.splitlines():
            if no_stamp:
                f.writelines(line + '\n')
            else:
                f.writelines('[{}] >  {}\n'.format(now(2),line))

def logBegin():
    with open(sesCache,'a') as f:
        f.writelines('\n\n[{}] >  {}\n'.format(now(2),' Beginning Script '.center(70,'v')))

def logEnd():
    with open(sesCache,'a') as f:
        f.writelines('[{}] >  {}\n\n'.format(now(2),' Script Complete! '.center(70,'^')))
        
def dprint(text):
    log(text)
    text = ' {} '.format(text)
    print('[{}] {}'.format(now(),text.center(100,'*')))
        
def printScore(pose,title,identifier='NOID',scorefxn=defaultScorefxn):
    title = identifier + ' - ' + title + ' Score'
    score = scorefxn(pose)
    output = '{} --> {:11.5f}'.format(title.ljust(40), score)
    log(output)
    with open(dec_dir,'a') as f:
        f.write('{}|{:011.5f}|{}|{}\n'.format(identifier,
                                            score,
                                            title,
                                            now(2)))
    if identifier in scoreDict:
        scoreDict[identifier].append((score, title))
    else:
        scoreDict[identifier] = [(score, title)]
    print(output)
    
def loadInPose(fileName,needParams=True):
    fileName = os.path.join(pdbCache,fileName)
    if not os.path.isfile(fileName):
        raise FileExistsError(fileName + ' is not a file')
    dprint('Loading In `{}` and Creating Pose'.format(fileName))
    pose = Pose()
    if needParams:
        params = ['LG.params']
        generate_nonstandard_residue_set(pose, params)
    pose_from_file(pose,fileName)
    return pose

def poseFrom(pose):
    newPose = Pose()
    newPose.assign(pose)
    return newPose

def namePose(pose,nameStr):
     pose.pdb_info().name(nameStr)


def createPyMolMover():
    pymol = PyMOLMover()
    return pymol


class CustomMover(pyrosetta.rosetta.protocols.moves.Mover):
    scorefxn = defaultScorefxn

    def __init__(self):
        super().__init__()
        self.identifier = 'NO_ID'
    
    def __str__(self):
        info = []
        n = len(self.__dict__)
        for key,val in self.__dict__.items():
            if (key in ['movemap']):
                continue
            
            infoStr = '{}: '.format(key)
            if isinstance(val,int):
                infoStr += '{:2d}'
            elif isinstance(val,float):
                infoStr += '{:7.1f}'
            else:
                infoStr += '{}'

            didFormat = False
            if key in ['bb_res', 'chi_res']:
                if val is not None:
                    if len(val) > 0:
                        infoStr = infoStr.format('SpecRes')
                        didFormat = True
            if not didFormat:
                infoStr = infoStr.format(val)
            info.append(infoStr)
        info[n//2] = info[n//2] + '\n'
        return ' | '.join(info)

    def get_name(self):
        return self.__class__.__name__

    def getIdName(self):
        return self.get_name() + '.ID-' + self.identifier

    
class FastRelaxMover(CustomMover):
    def __init__(self):
        super().__init__()

    def apply(self,pose):
        dprint('Beginning Fast Relax')
        fast_relax = FastRelax()
        fast_relax.set_scorefxn(self.scorefxn) 
        fast_relax.apply(pose)
    
    
class RepMinMover(CustomMover):
    chain = 'A'
    printCutoff = 15
    
    def __init__(self):
        super().__init__()
        self.repeats = 10
        self.kT = 1.0
        self.bb_all = False
        self.bb_range = None
        self.bb_res = None
        self.chi_all = False
        self.chi_range = None
        self.chi_res = None
        self.movemap = None
        
    def setMovemapBB(self,movemap,pose):
        movemap.set_bb(False)
        if self.bb_res is not None:
            for i in self.bb_res:
                pose_i = pose.pdb_info().pdb2pose(self.chain,i)
                movemap.set_bb(pose_i,True)
        elif self.bb_range is not None:
            begin, end = self.bb_range
            movemap.set_bb_true_range(begin,end)
        elif self.bb_all:
            movemap.set_bb(True) 

    def setMovemapChi(self,movemap,pose):
        movemap.set_chi(False)
        if self.chi_res is not None:
            for i in self.chi_res:
                pose_i = pose.pdb_info().pdb2pose(self.chain,i)
                movemap.set_chi(pose_i,True)
        elif self.chi_range is not None:
            begin, end = self.chi_range
            movemap.set_chi_true_range(begin,end)
        elif self.chi_all:
            movemap.set_chi(True) 
            
    def apply(self,pose):
        if self.repeats > self.printCutoff:
            dprint('Perfoming A Minimization Loop {:3d}'.format(self.repeats))
            log( '`--> {}'.format(self))
        movemap = MoveMap()
        self.setMovemapBB(movemap,pose)
        self.setMovemapChi(movemap,pose)
        self.movemap = movemap
        min_mv = MinMover()
        min_mv.movemap(movemap)
        min_mv.score_function(self.scorefxn)
        mc = MonteCarlo(pose,self.scorefxn,self.kT)
        trial_mv = TrialMover(min_mv,mc)
        rep_mv = RepeatMover(trial_mv,self.repeats)
        rep_mv.apply(pose)
        if self.repeats > self.printCutoff:
            printScore(pose,'Minimization Loop',self.identifier)

        
class SmallShearMover(CustomMover):
    min_repeats = 10

    def __init__(self):
        super().__init__()
        self.repeats = 50
        self.n_moves =5
        self.kT = 1.0
        self.angle = None
        self.bb_range = None
        
    def apply(self, pose):
        # dprint('Beginning Small & Shear Movers'.format(self.repeats))
        # log(' `--> {}'.format(self))

        min_mv = RepMinMover()
        if self.bb_range is None:
            min_mv.bb_all = True
        else:
            min_mv.bb_range = self.bb_range
        min_mv.repeats = self.min_repeats
        min_mv.identifier = self.identifier

        movemap = min_mv.movemap
        small_mv = SmallMover(movemap, self.kT, self.n_moves)
        shear_mv = ShearMover(movemap, self.kT, self.n_moves)
        if self.angle is not None:
            small_mv.angle_max('E', self.angle)
            small_mv.angle_max('L', self.angle)
            shear_mv.angle_max('E', self.angle)
            shear_mv.angle_max('L', self.angle)

        mc = MonteCarlo(pose, self.scorefxn, self.kT)

        seq_A = SequenceMover()
        seq_A.add_mover(small_mv)
        seq_A.add_mover(min_mv)
        trial_A = TrialMover(seq_A, mc)
        seq_B = SequenceMover()
        seq_B.add_mover(shear_mv)
        seq_B.add_mover(min_mv)
        trial_B = TrialMover(seq_B, mc)
        seq_total = SequenceMover()
        seq_total.add_mover(trial_A)
        seq_total.add_mover(trial_B)
        rep_mv = RepeatMover(seq_total, self.repeats)
        rep_mv.apply(pose)
        # printScore(pose,'Small & Shear Move',self.identifier)

        
class AnnealLoopMover(CustomMover):
    def __init__(self):
        super().__init__()
        self.cycles = 2        
        self.kT = 10
        self.heat_time = 3
        self.anneal_time = 4
        self.angle_max = 4.0
        self.kT_max = 100.0
        self.seqRepeats = 5
        self.numSmallShearRepeats = 5
        self.kT_ratio = 20
        self.angle_ratio = 10
        self.bb_range = None
                
    def apply(self,pose):
        dprint('Beginning Anneal Loop Mover')
        log(' `--> {}'.format(self))
        angles = ([self.angle_max] * self.heat_time
                  + [self.angle_max / self.angle_ratio] * self.anneal_time)
        kT2s = ([self.kT_max] * self.heat_time
                + [self.kT_max / self.kT_ratio] * self.anneal_time)
        cycleLen = len(angles)
        n = cycleLen* self.cycles
 
        ss_mv = SmallShearMover()
        ss_mv.repeats = self.seqRepeats
        ss_mv.n_moves = self.numSmallShearRepeats
        ss_mv.identifier = self.identifier
        if self.bb_range is not None:
            ss_mv.bb_range = self.bb_range
            
        mc = MonteCarlo(pose, self.scorefxn, self.kT)
       
        for i in range(n):
            ind = i % cycleLen
            if ind < self.heat_time: htcld = 'HEAT'
            else: htcld = 'COOL'
            angle = angles[ind]
            kT2 = kT2s[ind]
            ss_mv.angle = angle
            ss_mv.kT = kT2
            ss_mv.apply(pose)
            mc.boltzmann(pose)
            printScore(pose,
                       'Anneal Loop [{}] {:2d}/{:2d}'.format(htcld,i+1,n),
                       self.identifier)


class MutantPackMover(CustomMover):
    def __init__(self):
        super().__init__()
        self.resfile = None

    def apply(self,pose):
        dprint('Beginning Mutant Pack Mover')
        log(' `--> {}'.format(self))
        task = TaskFactory.create_packer_task(pose)
        parse_resfile(pose, task, self.resfile)
        pack_mv = PackRotamersMover(self.scorefxn, task)
        pack_mv.apply(pose)
        printScore(pose,'Mutant Pack',self.identifier)


class ResfileBuilder:
    resfile_dir = 'Resfiles'
    resfile_ext = 'resfile'
    rotamer_tag = 'NATAA'
    mutate_tag = 'PIKAA {}'
    chain = 'A'
    ligand_chain = 'X'
    line_fmt = '{:3d}  {}  {}\n'
    
    def __init__(self):
        self.filename = 'unnamed'
        self.packable_residues = []
        self.mutable_residues = []
        self.mut_liberal = False
        self.pose = None
        mkDir(self.resfile_dir)

    def getMutDict(self):
        if self.mut_liberal: return liberalMutMap
        else: return conservMutMap 

    def getFullFilename(self):
        return  self.filename + '.' + self.resfile_ext
        
    def getResfilePath(self):
        print('ResfileBuilder.getResfilePath: Joining {} and {}'.\
              format(self.resfile_dir, self.getFullFilename()))
        return os.path.join(self.resfile_dir,self.getFullFilename())

    def getFileHeader(self):
        text = ('# {}\n'.format(self.getFullFilename())
                + 'NATRO\nSTART\n\n'
                + '# Auto Generated Resfile by ResfileBuilder class\n' 
                + '# {}\n\n'.format(now()))
        return text
    
    def build(self):
        dprint('ResfileBuilder.build: Writing File --> {}'.format(self.filename))
        if self.mut_liberal: mutDict = liberalMutMap
        else: mutDict = conservMutMap
        with open(self.getResfilePath(),'w') as rfile:
            rfile.write(self.getFileHeader())
            if len(self.packable_residues) > 0:
                rfile.write('# Packable Residues:\n')
            for res in self.packable_residues:
                line = self.line_fmt.format(res, self.chain, self.rotamer_tag)
                rfile.write(line)
            if len(self.mutable_residues) > 0:
                rfile.write('# Mutable Residues:\n')                
            for res in self.mutable_residues:
                line = self.line_fmt.format(res, self.chain, self.mutate_tag)
                poseNum = self.pose.pdb_info().pdb2pose(self.chain,res)
                aa = self.pose.residue(poseNum).name1()
                mutRes = mutDict[aa]
                if len(mutRes) > 0:
                    line = line.format(''.join(mutRes))
                    rfile.write(line)

    @classmethod
    def pocketRotamerResfile(cls):
        print('ResfileBuilder.pocketRotamerResfile: Creating Pocket Rotamer Resfile')
        name = 'pocket_rotamer'
        filepath = ResfileBuilder.resfilePath(name)
        if os.path.isfile(filepath):
            return filepath
        builder = cls()
        print('ResfileBuilder.pocketRotamerResfile: name --> {}'.format(name))
        builder.filename = name
        print('ResfileBuilder.pocketRotamerResfile: builder.filename --> {}'.\
              format(builder.filename))
        builder.packable_residues = pocketResNums
        builder.build()
        return builder.getResfilePath()

    @classmethod
    def fullRotamerResfile(cls):
        print('ResfileBuilder.fullRotamerResfile: Creating Full Rotamer Resfile')
        name = 'full_rotamer'
        filepath = ResfileBuilder.resfilePath(name)
        if os.path.isfile(filepath):
            return filepath
        builder = cls()
        builder.filename = name
        builder.packable_residues = range(firstResNum, lastResNum + 1)
        builder.build()
        return builder.getResfilePath()

    @classmethod
    def ligandRotamerResfile(cls):
        name = 'ligand_rotamer'
        filepath = ResfileBuilder.resfilePath(name)
        if os.path.isfile(filepath):
            return filepath
        builder = cls()
        builder.filename = name
        builder.packable_residues = [1]
        builder.chain = 'X'
        builder.build()
        return builder.getResfilePath()
        
    @classmethod
    def resfileFromDecoySpecs(cls, pose, residues, liberal, identifier, cycle):
        builder = cls()
        builder.mutable_residues = residues
        builder.filename = 'decoy-{}.{:02d}'.format(identifier,cycle)
        builder.pose = pose
        builder.mut_liberal = liberal
        builder.build()
        return builder.getResfilePath()    
    
    @staticmethod
    def resfilePath(filename):
        suffix = '.' + ResfileBuilder.resfile_ext
        if not filename.endswith(suffix):
            filename += suffix
        return os.path.join(ResfileBuilder.resfile_dir,filename)


class MutationMinimizationMover(CustomMover):
    anneal_bb_range = None
    decoy_count = 0
    fast_relax_mv = FastRelaxMover()

    def __init__(self):
        super().__init__()
        self.mut_pattern = [[]]
        self.kT = 1.0
        self.identifier = MutationMinimizationMover.decoy_count
        self.liberal = []
        MutationMinimizationMover.decoy_count += 1
        
    def apply(self, pose):
        dprint(('MMM.ID {} - Beginning Mutation '
                'Minimization Mover').format(self.identifier))
        log(' `--> {}'.format(self))
        mc = MonteCarlo(pose, self.scorefxn, self.kT)
        n = len(self.mut_pattern)
        for i,mut_residues in enumerate(self.mut_pattern):
            log('MMM.ID {} - Loop {:2d}/{:2d}'.format(
                self.identifier, i+1, n))
            # for each decoy create a mover that:
            #   1. mutates the specified residues with resfile
            r_file = ResfileBuilder.resfileFromDecoySpecs(
                pose, mut_residues, self.liberal[i],
                self.identifier, i)
            mut_mv = MutantPackMover()
            mut_mv.resfile = r_file
            mut_mv.identifier = self.identifier
            #   2. repacks rotomers for all pocket residues, use movemap with MinMover
            repack_mv = RepMinMover()
            repack_mv.chi_res = pocketResNums
            repack_mv.repeats = 50
            repack_mv.identifier = self.identifier
            #   3. do small/shear anneal loop
            anneal_mv = AnnealLoopMover()
            anneal_mv.bb_range = self.anneal_bb_range
            anneal_mv.identifier = self.identifier
            #   4. minimize pocket rotamers (same as 2)
            #   5. pack ligand
            lig_mv = MutantPackMover()
            lig_mv.resfile = ResfileBuilder.ligandRotamerResfile()
            lig_mv.identifier = self.identifier
            #   5. minimize backmobe
            min_mv = RepMinMover()
            min_mv.bb_all = True
            min_mv.repeats = 50
            min_mv.identifier = self.identifier

            # debug assignments
            debug = False
            if debug:
                min_mv.repeats, repack_mv.repeats = (1, 1)
                SmallShearMover.min_repeats = 1
            
            seq_mv = SequenceMover()
            seq_mv.add_mover(mut_mv)
            seq_mv.add_mover(repack_mv)
            seq_mv.add_mover(anneal_mv)
            seq_mv.add_mover(repack_mv)
            seq_mv.add_mover(lig_mv)
            seq_mv.add_mover(min_mv)
            trial_mv = TrialMover(seq_mv, mc)
            trial_mv.apply(pose)
            printScore(pose,
                       'Mut & Min #{:02d}'.format(i+1),
                       self.identifier)
            
        self.fast_relax_mv.apply(pose)
        printScore(pose,'Mut & Min, FastRelaxed',self.identifier)

    @staticmethod
    def randSample(n,lst):
        length = len(lst)
        temp_list = list(lst)
        sample = []
        for i in range(n):
            ind = random.randint(0, length - 1 - i)
            sample.append(temp_list[ind])
            del temp_list[ind]
        return sample, temp_list

    @staticmethod
    def makeMutPattern(numDecoys, resPerDecoyList):
        rand_samples = [[] for __ in range(numDecoys)]
        for i,(num_res, __) in enumerate(resPerDecoyList):
            remaining_res = []
            for decoyNum in range(numDecoys):
                if len(remaining_res) < num_res:
                    remaining_res = list(pocketResNums)
                if True:
                    smp, remaining_res = MutationMinimizationMover.\
                                         randSample(num_res, remaining_res)
                else:
                    smp, __ = MutationMinimizationMover.\
                              randSample(num_res, pocketResNums)
                rand_samples[decoyNum].append(smp)
        return rand_samples

def setup():
    dprint('Setting Things Up')
    date_id = now(3)

    original_pdb_file = 'new_3vi8_complex.pdb'
    try:
        origPose = loadInPose(original_pdb_file)
        namePose(origPose,'original')
    except FileExistsError as err:
        print('setup: Failed, cannot load in initial pose')
        raise

    fast_relaxed_pdb_file = '3vi8_complex_fastRelaxed.pdb'
    try:
        fastRelaxedPose = loadInPose(fast_relaxed_pdb_file)
    except FileExistsError as err:
        fastRelaxedPose = poseFrom(origPose)
        fastRelax(fRelaxPose)
        fRelaxPose.dump_pdb(fRelaxFile)
        namePose(fRelaxPose,'orig_relaxed')

    numDecoys = 16
    resPerDecoyList = [
        (4, True), (4, True),
        (2, False), (2, False),
        (2, False), (2, False),
    ]
    rand_samples = MutationMinimizationMover.makeMutPattern(
        numDecoys, resPerDecoyList)
    log('Random Samples Arr:')
    log(pprint.pformat(rand_samples), no_stamp=True)

    MutationMinimizationMover.anneal_bb_range =(
        pocketResNums[0] - 10,
        pocketResNums[-1] + 10)
    mm_mvs = []
    for i in range(numDecoys):
        mm_mv = MutationMinimizationMover()
        mm_mv.liberal = [boool for (__, boool) in resPerDecoyList]
        mm_mv.identifier =  date_id  + '-' + 'DEC_{:02d}'.format(i)
        mm_mv.mut_pattern = rand_samples[i]
        mm_mvs.append(mm_mv)

    mkDir('Decoys')
    mkDir(os.path.join('Decoys',date_id))

    global dec_dir
    dec_dir = os.path.join('Decoys',date_id,'scorefile.txt')
    with open(dec_dir,'w') as f:
        f.write('Beginning Score Log For Decoys: {}\n\n'.format(date_id))
    
    return (date_id, origPose, fastRelaxedPose, mm_mvs)
    
def main():
    global dateId
    dateId, origPose, fastRelaxedPose, mm_mvs = setup()
    startPose = fastRelaxedPose
    printScore(origPose,'Original Pose')
    printScore(fastRelaxedPose,'Fast Relaxed Pose')
    file_template = os.path.join('Decoys',dateId,
                                 'output-{}-DEC'.format(dateId))

    ######################################################################
    ### Single Stream Version
    # jd = PyJobDistributor(file_template, len(mm_mvs), defaultScorefxn)
    # print('main: JD sequence = ',jd.sequence)
    # jd.native_pose = startPose
    # working_pose = Pose()
    # ind = 0 
    # breakOnNext = False
    # while True:
    #     if ind > len(mm_mvs):
    #         raise IndexError('Ran out or MM Movers before '
    #                          'the end of the job distributor.')
    #     dprint('Beginning Decoy # {:d}'.format(ind + 1))
    #     print('main: JD  sequence ', jd.sequence) # debug
    #     working_pose.assign(startPose)
    #     mm_mvs[ind].apply(working_pose)
    #     jd.output_decoy(working_pose)
    #     ind += 1
    #     if breakOnNext: break
    #     if jd.job_complete: breakOnNext = True
    ######################################################################

    ######################################################################
    ### Multiprocessor Version
    n = len(mm_mvs)

    def run(i):
        pose = poseFrom(startPose)
        dprint('Beginning Decoy # {:d}'.format(i))
        mm_mvs[i].apply(pose)
        fname = file_template + '_{:02d}.pdb'.format(i)
        pose.dump_scored_pdb(fname,defaultScorefxn)
        return
    parmap(run,range(n))
    ######################################################################

    dprint('Finished!')
    log('Score Log --v--v--v')
    log(pprint.pformat(scoreDict), no_stamp=True)

def comparePDBs():
    global dateId
    dateId = now(3)

    original = loadInPose('3vi8_complex_fastRelaxed.pdb')
    new = loadInPose('lowest_e_decoy.pdb')

    original_no_lig = loadInPose('3vi8_complex_fastRelaxed_no_ligand.pdb')
    new_no_lig = loadInPose('lowest_e_decoy_no_ligand.pdb')

    names = [['Starting Complex', 'Starting Prot Alone'],
             ['Mutant Complex', 'Mutant Protein Alone']]
    poses = [[original, original_no_lig],
             [new, new_no_lig]]
    fname = ['new_3vi8_complex_no_ligand_relaxed.pdb',
             'lowest_e_decoy_no_ligand_relaxed.pdb']

    # def relaxNoLigands(i):
    #     pose = poseFrom(poses[i][1])
    #     FastRelaxMover().apply(pose)
    #     pose.dump_scored_pdb(os.path.join('AlgorithmCache',
    #                                       'PDBs',fname[i],),
    #                          defaultScorefxn)
    #
    n = len(fname)
    # # parmap(relaxNoLigands,range(n))
    #
    for i in range(n):
         poses[i][1] = loadInPose(fname[i],needParams=False)

    sequences = [p.sequence() for p, __ in poses]
    paired = zip(sequences[0],sequences[1])
    for i, (a, b) in enumerate(paired):
        # print('i,(a,b) : {},({},{})'.format(i,a,b))
        if not a == b:
            pdb_num = poses[0][0].pdb_info().pose2pdb(i+1).split(' ')
            pdb_num = int(pdb_num[0])
            # print('pdb_num : {}'.format(pdb_num))
            out = ('MUTATION: @ {:3d},'
                   ' {} ---> {}'.format(pdb_num,a,b))
            print(out)
            log(out)

    scores = [[defaultScorefxn(p) for p in pair] for pair in poses]

    paired = [list(zip(n,s)) for n,s in zip(names,scores)]
    pprint.pprint(paired)
    log(pprint.pformat(paired))

    def reu_to_g(x): return ((0.57 * x) - 600) / 1000

    def calc_del_del(x): return (x[0][1] - x[0][0]) - (x[1][1] - x[1][0])

    deldelRose = calc_del_del(scores)
    print('deltadelta(RoseEng) = {:11.5f}'.format(deldelRose))
    log('deltadelta(RoseEng) = {:11.5f}'.format(deldelRose))

    del_gs = [[reu_to_g(p) for p in pair] for pair in scores]
    deldelG = calc_del_del(del_gs)
    print('deltadeltaG (kcal/mol) = {:11.5f}'.format(deldelG))
    log('deltadeltaG (kcal/mol) = {:11.5f}'.format(deldelG))

    print('\n\n\n')
       
    
if __name__ == '__main__':
    logBegin()
    # main()
    comparePDBs()
    logEnd()
    print('Commiting Project')
    subprocess.call(('bash ~/gg.sh \"Auto Commit After Program Completion '
                     '(Run ID --> {})\"'.format(dateId)),
                    shell=True)


 



