## DV calculations

data_dir = data_dir=path.join('/Users/zeynepenkavi/Documents/PoldrackLabLocal/Self_Regulation_Ontology/Data/','Retest_'+release_date)
    
# Individual_Measures/
from selfregulation.utils.data_preparation_utils import save_task_data
save_task_data(data_dir, data)

#metadata/
#references/
meta_dir = path.join(data_dir,'metadata')
reference_dir = path.join(data_dir,'references')
from os import makedirs
if not path.exists(meta_dir):
    makedirs(meta_dir)
if not path.exists(reference_dir):
    makedirs(reference_dir)

#demographics.csv
#demographics_ordinal.csv
demog_data = extract_experiment(data,'demographics_survey')
from process_demographics import process_demographics
demog_data = process_demographics(demog_data, data_dir, meta_dir)

#alcohol_drugs.csv
#alcohol_drugs_ordinal.csv
alcohol_drug_data = extract_experiment(data,'alcohol_drugs_survey')
from process_alcohol_drug import process_alcohol_drug
alcohol_drug_data = process_alcohol_drug(alcohol_drug_data, data_dir, meta_dir)

#health.csv 
#health_ordinal.csv
health_data = extract_experiment(data,'k6_survey')
from process_health import process_health
health_data = health_data.where((pd.notnull(health_data)), None)
health_data = process_health(health_data, data_dir, meta_dir)

#demographic_health.csv - done
target_data = pd.concat([demog_data, alcohol_drug_data, health_data], axis = 1)
target_data.to_csv(path.join(data_dir,'demographic_health.csv'))

#reference/demographic_health_reference.csv - done
np.savetxt(path.join(reference_dir,'demographic_health_reference.csv'), target_data.columns, fmt = '%s', delimiter=",")
    
#items.csv.gz - done
from selfregulation.utils.data_preparation_utils import get_items
items_df = get_items(data)
subjectsxitems = items_df.pivot('worker','item_ID','coded_response')
assert subjectsxitems.shape[1] == 594, "Wrong number of items found"
items_df.to_csv(path.join(data_dir, 'items.csv.gz'), compression = 'gzip')

#subject_x_items.csv - done
subjectsxitems.to_csv(path.join(data_dir, 'subject_x_items.csv'))

from os import chdir
chdir('/Users/zeynepenkavi/Documents/PoldrackLabLocal/Self_Regulation_Ontology/Data')
from selfregulation.utils.data_preparation_utils import convert_var_names
convert_var_names(subjectsxitems)
assert np.max([len(name) for name in subjectsxitems.columns])<=8, "Found column names longer than 8 characters in short version"

readme_lines = []
readme_lines += ["demographics_survey.csv: demographic information from expfactory-surveys\n\n"]
readme_lines += ["alcohol_drug_survey.csv: alcohol, smoking, marijuana and other drugs from expfactory-surveys\n\n"]
readme_lines += ["ky_survey.csv: mental health and neurological/health conditions from expfactory-surveys\n\n"]
readme_lines += ["items.csv.gz: gzipped csv of all item information across surveys\n\n"]
readme_lines += ["subject_x_items.csv: reshaped items.csv such that rows are subjects and columns are individual items\n\n"]
readme_lines += ["Individual Measures: directory containing gzip compressed files for each individual measures\n\n"]    

readme = open(path.join(data_dir, "README.txt"), "w")
readme.writelines(readme_lines)
readme.close()