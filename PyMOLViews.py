import pymol

# 3VI8 Specific Global Variables
resi_first = 202
resi_last = 468
resi_pocket = [241, 247, 250, 251, 254, 255, 272, 273, 275, 276, 279, 280,\
               321, 325, 330, 332, 333, 334, 339, 343, 344, 354, 355, 358] 
sel_pocket = '(resi {})'.format('+'.join([str(num) for num in resi_pocket]))

views = {'pocket_1':'''\
     -0.113475665,    0.939743817,    0.322399676,\
     -0.929277480,   -0.215191364,    0.300164282,\
      0.351477772,   -0.265553772,    0.897729993,\
      0.000084354,   -0.000419226,  -61.812778473,\
     10.476990700,    5.397646904,   -9.961334229,\
     26.753036499,   96.871490479,  -20.000000000'''}

def setup():
    cmd.reset() # reset view
    hideAll()
    util.performance(0) # maximum quality
    cmd.bg_color('white') # white background
    cmd.set('cartoon_fancy_helices','1',quiet=0) # fancy helixes
    cmd.set('surface_color_smoothing_threshold', 0.7)
    cmd.set('surface_color_smoothing',20)
    cmd.set('transparency_mode',3,quiet=0)
    cmd.set('surface_quality',2)
    cmd.set('surface_cavity_mode', 2)
    cmd.set('cavity_cull', 150)    

def hideAll():
    cmd.hide('everything', '*')

def hideHydro():
    cmd.hide('(hydro)')
    
def showStick(sel,color):
    cmd.show('stick', sel)
    cmd.color(color, sel)

def showRibbon(sel,color):
    cmd.show('ribbon',sel)
    cmd.color(color,sel)
    
def showCartoon(sel,color,transp=0):
    cmd.show('cartoon', sel)
    cmd.color(color, sel)
    cmd.set('cartoon_transparency',transp)

def showSphere(sel,color,transp=0):
    cmd.show('sphere',sel)
    smd.color(color,sel)
    cmd.set('sphere_transparency',transp)
    
def showSurface(sel,color,transp=0):
    cmd.show('surface', sel)
    cmd.set('transparency', transp, sel)
    cmd.color(color_protein, sel_protein)
    # util.cnc(sel_protein)
    
def saveIimage(name='UntiledImage',ray=1):
    print('Saving Image {}.png ...'.format(name))
    if ray: cmd.ray()
    cmd.png(name)
    print('Saving Done.')

def printHeadder(number='?', title='Untitled Section'):
    width = 70
    print('\n' + '*'*width)
    print('  Section {:d}: {}  '.format(number,title).center(width,'*'))
    print('*'*width + '\n')

def setVview(view_ref):
    if view_ref in views:
        cmd.set_view(views[veiw_ref])
        cmd.deselect()
    else:
        print('ERROR: Not a valid selection')

def selectProtein(name,obj):
    cmd.select(name,'(br. (n. C+O+N+CA)) & {}'.format(obj))
    cmd.deselect()

def selectLigand(name,obj,protein):
    # FIXME - Could use something better to select the ligand ... LG1?
    cmd.select(name,'{} & !{}'.format(obj, protein))
    cmd.deselect()
    
def selResNear(obj_complex,radius=5):
    sel_prot = 'prot_{}'.format(obj_complex)
    sel_lig = 'lig_{}'.format(obj_complex)
    sel_nearby = 'near_{}'.format(obj_complex)
    selectProtein(sel_prot,obj_complex)
    selectLigand(sel_lig,obj_complex,sel_prot)
    cmd.select(sel_nearby,'(br. (({} & !(n. C+O+N+CA)) w. {:f} of {})) & !(n. C+O+N)'.format\
               (sel_prot, radius, sel_lig))
    cmd.deselect()
    stored.list = []
    cmd.iterate('{} & n. CA'.format(sel_nearby),\
                'stored.list.append((resi,resn))')
    out = 'pocket_resi = [{}]'.format(', '.join([str(ele[0]) for ele in stored.list]))
    print(out)

cmd.extend('selResNear',selResNear)
    
    
def main(section=0, render=0):
    sec_number = 1
    if not section == 0: sec_number = section

    if section == 0 or section == 1:
        print_sec_headder(sec_number,'Setup')
        setup()
        sec_number += 1

    if section == 0 or section == 2:
        print_sec_headder(sec_number,'Cartoon View')
        hide_all()
        show_ligand()
        show_ribbon()
        set_view(whole_view)
        if render: save_image('cartoon')
        sec_number += 1

    if section == 0 or section ==  3:
        print_sec_headder(sec_number,'Surface Pocket View')
        hide_all()
        show_ligand()
        show_surface()
        set_view(pocket_view_1)
        if render: save_image('surface')
        show_pah()
        if render: save_image('surface_PAH')
        sec_number += 1

    if section == 0 or section == 4:
        print_sec_headder(sec_number,'Pocket View With Cartoon')
        hide_all()
        show_ligand()
        show_ribbon(0.5)
        show_surface(0.3)
        set_view(whole_view)
        if render: save_image('cartoonAndPocket')
        show_pah()
        if render: save_image('cartoonAndPocket_PAH')
        sec_number += 1

    if section == 0 or section == 5:
        print_sec_headder(sec_number,'Cutaway Pocket View #1')
        hide_all()
        show_ligand()
        show_surface(0.3)
        set_view(cutaway_view_1_1)
        if render: save_image('cutaway1', 0)
        show_pah()
        if render: save_image('cutaway1_PAH', 0)
        sec_number += 1

    if section == 0 or section == 6:
        print_sec_headder(sec_number,'Cutaway Pocket View #2')
        hide_all()
        show_ligand()
        show_surface(0)
        set_view(cutaway_view_2)
        if render: save_image('cutaway2')
        show_pah()
        if render: save_image('cutaway2_PAH')
        sec_number += 1

    if section == 0 or section == 7:
        print_sec_headder(sec_number,'Nearby Residues')
        hide_all()
        show_ligand()
        show_nearby_residues()
        if render: save_image('residues')
        show_pah()
        if render: save_image('residues_PAH')
        sec_number += 1
                                                              
    print('*'*50+ ' '*2 + 'DONE' + ' '*2 + '*'*50)
            
    
cmd.extend('main', main)

