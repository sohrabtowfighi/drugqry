# DrugQry - Tool for checking drug interactions
# Provided as is with no warranty whatsoever, 
# not even for intended purpose.
# Sohrab Towfighi, MD Candidate at Univ. Toronto
# GNU GPL V2 Licence. (c) 2017
docstring = """
   DrugQry - Provided as is with no warranty 
   whatsoever not even for intended purpose.
   If you do not have the full_database.db file,
   get the "full database.xml" file from DrugBank,
   then run "python3 drugqry.py -s". It will take
   a few hours since parsing XML is slow.

   To query the full_database.db, do not pass -s 
   as the first argument, but instead provide a 
   comma separated list of medications, which
   DrugQry will check for interactions.
"""
import xml.etree.ElementTree as ET
import pdb
import sqlite3
import sys
prefix = '{http://www.drugbank.ca}'

class Drug():
    def __init__(self):
        self.name = ''
        self.mechanism = ''
        self.indication = ''
        self.pharmacodynamics = ''
        self.half_life = ''
        self.interactions = list()

def create_drugs_table(connection):
    QRY = """CREATE TABLE drugs
             (name text PRIMARY KEY, 
              mechanism text, 
              indication text, 
              half_life text,
              pharmacodynamics text)"""
    cursor = connection.cursor()
    cursor.execute(QRY)
    connection.commit()
    
class Interaction():        
    def __init__(self):
        self.interacts_with = ''
        self.drugbank_id = ''
        self.description = ''

def create_interactions_table(connection):
    QRY = """CREATE TABLE interactions
             (drug_name text,
              interacts_with text,               
              description text)              
              """
    cursor = connection.cursor()
    cursor.execute(QRY)
    connection.commit()
    
def add_interaction_to_db(interaction, connection):
    QRY = """ INSERT INTO interactions(drug_name, interacts_with, description)
              VALUES(?,?,?) """
    cursor = connection.cursor()
    values = [interaction.drug_name, interaction.interacts_with,
              interaction.description]
    cursor.execute(QRY, values)
    connection.commit()


def add_drug_to_db(drug, connection):
    QRY = """INSERT INTO drugs (name, mechanism, indication, half_life, 
                                pharmacodynamics)
             VALUES(?,?,?,?,?)"""
    cursor = connection.cursor()
    values = [drug.name, drug.mechanism, drug.indication, drug.half_life, 
              drug.pharmacodynamics]
    cursor.execute(QRY, values)
    connection.commit()

def convert_drug_from_xml_to_object(xml_datastruct, my_drug):
    for prop in xml_datastruct:        
        if prop.tag == prefix + 'name':            
            my_drug.name = prop.text
        elif prop.tag == prefix + 'mechanism':
            my_drug.mechanism = prop.text
        elif prop.tag == prefix + 'indication':
            my_drug.indication = prop.text
        elif prop.tag == prefix + 'half-life':
            my_drug.half_life = prop.text
        elif prop.tag == prefix + 'pharmacodynamics':
            my_drug.pharmacodynamics = prop.text
        elif prop.tag == prefix + 'drug-interactions':             
            for intrxn in prop.getchildren():                
                my_intrxn = convert_interaction_from_xml_to_object(intrxn)
                my_intrxn.drug_name = my_drug.name
                my_drug.interactions.append(my_intrxn) 
    return my_drug
    
def convert_interaction_from_xml_to_object(xml_datastruct):    
    my_interaction = Interaction()
    for property in xml_datastruct.getchildren():  
        if property.tag == prefix + 'name':
            my_interaction.interacts_with = property.text
        elif property.tag == prefix + 'description':
            my_interaction.description = property.text
    if len(xml_datastruct.getchildren()) == 0:
        if xml_datastruct.tag == prefix + 'name':
            my_interaction.interacts_with = xml_datastruct.text
        elif xml_datastruct.tag == prefix + 'description':
            my_interaction.description = xml_datastruct.text  
    return my_interaction
    
def add_drug(xml_of_drug, conn): # each elem is an XML element matching a drug
    my_drug = Drug()
    prefix = '{http://www.drugbank.ca}'
    prefix_len = len(prefix)
    convert_drug_from_xml_to_object(xml_of_drug, my_drug)          
    # add the drug
    add_drug_to_db(my_drug, conn)
    # iterate through all the drug's interactions and add them
    for interaction in my_drug.interactions:
        add_interaction_to_db(interaction, conn)                

def count_drugs(connection):
    cursor = connection.cursor()
    cursor.execute("select count(*) from drugs")
    print("Drugs in database:" + str(cursor.fetchone()[0]))
    
def setup_sql_db(path_to_xml, path_to_db):
    conn = sqlite3.connect(path_to_db)
    create_drugs_table(conn)
    create_interactions_table(conn)    
    cursor = conn.cursor()
    tree = ET.parse('full_database.xml')
    root = tree.getroot()
    for xml_drug in root:
        add_drug(xml_drug, conn)
        count_drugs(conn)
    conn.close()

def capitalize_name(drug_name):
    drug_name = drug_name.lower()
    drug_name = drug_name[:1].upper() + drug_name[1:]
    return drug_name

def standardize_capitalization_in_list(drug_list):
    new_drug_list = list()
    for drug in drug_list:
        new_drug_list.append(capitalize_name(drug))
    return new_drug_list

def check_drug_in_db(drug_name, conn):
    QRY = "SELECT COUNT(*) FROM drugs WHERE name = (?)"
    cur = conn.cursor()
    cur.execute(QRY, (drug_name,))
    row = cur.fetchone()
    if row[0] == 1:
        return True
    else:
        return False

def get_interactions(drug_name, conn, drugs_to_check):
    if not drugs_to_check: # list is empty or None passed
        return
    QRY = ("SELECT drug_name, interacts_with, description FROM " + 
           "interactions WHERE drug_name = (?) AND (interacts_with = (?)")
    for i in range(1, len(drugs_to_check)):
        QRY = QRY + " OR interacts_with = (?) "
    QRY = QRY + ")"
    interactions_list = list()
    cur = conn.cursor()
    cur.execute(QRY, [drug_name]+drugs_to_check)
    rows = cur.fetchall()
    for intxn in rows:
        interaction = Interaction()
        interaction.drug_name = intxn[0]
        interaction.interacts_with = intxn[1]
        interaction.description = intxn[2]
        interactions_list.append(interaction)
    return interactions_list

def print_interaction(interaction):
    output = interaction.drug_name + ' interacts with ' + interaction.interacts_with
    output = output + '\n' + interaction.description + '\n'
    return output

def main(comma_separated_drug_list):
    drug_list = comma_separated_drug_list.split(',')
    drug_list = standardize_capitalization_in_list(drug_list)
    conn = sqlite3.connect(db_file)
    # check that the drugs in the drug list can be found in the database
    for drug in drug_list:
        if check_drug_in_db(drug, conn) == False:
            return(drug + 
                   " is not in database. Remove it/fix spelling and try again.")
    # compare first drug to all others
    # then compare second drug to all others excluding first drug
    # then compare third drug to all others excluding first and 2nd drug
    # etc.
    relevant_interactions = list()
    for i in range(0,len(drug_list)-1):
        drug = drug_list[i]
        all_others = drug_list[i+1:]
        intxns = get_interactions(drug, conn, all_others)
        if intxns: # none empty
            relevant_interactions = relevant_interactions + intxns
    interactions_report = ''
    for interaction in relevant_interactions:
        interactions_report += print_interaction(interaction)
    return interactions_report
    
if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) == 0:
        print(docstring)
        exit(0)
    if args[0] == '-s':
        source_xml_file = 'full database.xml'
        destination_db_file = 'full_database.db'
        setup_sql_db(source_xml_file, destination_db_file)
    else:
        db_file = 'full_database.db'
        comma_separated_drug_list = args[0]
        output = main(comma_separated_drug_list)
        print(output)