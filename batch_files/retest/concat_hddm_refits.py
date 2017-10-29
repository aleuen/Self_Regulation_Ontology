import glob
import os
import pandas

#retest
DVs = pandas.DataFrame()
valence = pandas.DataFrame()
for exp_file in glob.glob(os.path.join('/scratch/users/zenkavi/tmp/data/hddm_refits', '*hddm_refit*DV.json')):
    base_name = os.path.basename(exp_file)
    exp = base_name.replace('_hddm_refit_DV.json','')
    print('Hddm refit: Extracting %s DVs' % exp)
    exp_DVs = pandas.read_json(exp_file)
    exp_valence = pandas.read_json(exp_file.replace('.json','_valence.json'))
    exp_DVs.columns = [exp + '.' + c for c in exp_DVs.columns]
    exp_valence.columns = [exp + '.' + c for c in exp_valence.columns]
    DVs = pandas.concat([DVs,exp_DVs], axis = 1)
    valence = pandas.concat([valence,exp_valence], axis = 1)

DVs.to_json('/scratch/users/zenkavi/tmp/data/mturk_hddm_refit_DV.json')
valence.to_json('/scratch/users/zenkavi/tmp/data/mturk_hddm_refit_DV_valence.json')
