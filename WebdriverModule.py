#!usr/bin/python


"""
    Coregulation Data Harvester--A tool for organizing and predicting 
    Tetrahymena thermophila gene annotations 

    Copyright (C) 2015-2017 Lev M Tsypin

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version. 

    If you choose to publish research based on this software, or distribute
    any work containing it, please make a notice of the copyright holder's 
    attribution. If you derivitize or modify the software, please make 
    a note that it is a derived work.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""



__author__ = 'Lev Tsypin (Ltsypin@gmail.com)'
__version__ = '1.2.1'

""" The Webbrowser module for my TranscriptomicsDataHarvester
    It uses selenium to access the websites and data. It also uses the NCBI
    BLAST API, accessing it through Biopython.
    
    Inputs: 
        -gene of interest in the for of TTHERM_ID 
        -lowerbound for z-scores
         (i.e. at which point should the program no longer record genes as
         coregulated)
    
    Outputs: 
        -XML files with BLASTx data for the list of coregulated genes,
         written in to os.path.abspath('BLASTresults') with file names taking
         the form TTHERM_ID_blastx_date.XML

        -coregs_zscores_cDNA_list, a list of lists with each small list having
         [TTHERM_ID, common name, description, z-score, cDNA from the TGD (or
         FGD if the gene is not available at the TGD)]

"""


# imports
import sys
import os
import site
import time
import platform
import pdb
import shutil
import CoregulationDataHarvester
import BLASTmod
import requests
import bs4
import logging
import re
# from Bio.Blast import NCBIWWW
import dill
import filename_generator

if platform.system() == 'Windows':
    from win32com.shell import shell, shellcon

class Coreg_Gene:
    # This is where the data for each gene in a co-regulated set lives.
    # Basically, it gathers all existing information from the TGD and
    # TetraFGD. If there is something else that should be stored, this
    # is the place.

    # It would actually make sense to store the CDH predictions here...
    # That way, when potentially there is functionality to build specialized
    # reports that are not constrained to a single co-regulated set, it would
    # be easier to retrieve that data. But there is a
    # problem: the summaries depend on which taxa were BLASTed against. The
    # current setup is agnostic to this, which is a large advantage. If I am
    # to change this, I would need to create a new set of objects. I think I
    # will wait to implement this until it is necessary.

    def __init__(self, TTHERM_ID, zscore):
        self._TTHERM_ID = TTHERM_ID
        self._common_name = ''
        self._description = ''
        self._gene_ontology = ''
        self._zscore = zscore
        self._cDNA = ''
        self._protein = ''
        # self._blastp_ortho_summary = ''
        # self._blastp_para_summary = ''
        # self._blastp_mix_summary = ''
        # self._blastp_mix_long_summary = ''
        # self._blastx_ortho_summary = ''
        # self._blastx_para_summary = ''
        # self._blastx_mix_summary = ''
        # self._blastx_mix_long_summary = ''

    @property
    def TTHERM_ID(self):
        return self._TTHERM_ID
    @property
    def common_name(self):
        return self._common_name

    @common_name.setter
    def common_name(self, common_name):
        self._common_name = common_name

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, description):
        self._description = description

    @property
    def gene_ontology(self):
        return self._gene_ontology

    @gene_ontology.setter
    def gene_ontology(self, gene_ontology):
        self._gene_ontology = gene_ontology

    @property 
    def zscore(self):
        return self._zscore

    @property 
    def cDNA(self):
        return self._cDNA

    @cDNA.setter
    def cDNA(self, cDNA):
        self._cDNA = cDNA

    @property
    def protein(self):
        return self._protein

    @protein.setter
    def protein(self, protein):
        self._protein = protein

    # @property
    # def blastx_ortho_summary(self):
    #     return self._blastx_ortho_summary
    
    # @blastx_ortho_summary.setter
    # def blastx_ortho_summary(self, blastx_ortho_summary):
    #     self._blastx_ortho_summary = blastx_ortho_summary
    
    # @property
    # def blastx_para_summary(self):
    #     return self._blastx_para_summary
    
    # @blastx_para_summary.setter
    # def blastx_para_summary(self, blastx_para_summary):
    #     self._blastx_para_summary = blastx_para_summary

    # @property
    # def blastp_mix_summary(self):
    #     return self._blastp_mix_summary
    
    # @blastp_mix_summary.setter
    # def blastp_mix_summary(self, blastp_mix_summary):
    #     self._blastp_mix_summary = blastp_mix_summary    
    
    # @property
    # def blastx_mix_long_summary(self):
    #     return self._blastx_mix_long_summary
    
    # @blastx_mix_long_summary.setter
    # def blastx_mix_long_summary(self, blastx_mix_long_summary):
    #     self._blastx_mix_long_summary = blastx_mix_long_summary 

    # @property
    # def blastp_ortho_summary(self):
    #     return self._blastp_ortho_summary
    
    # @blastp_ortho_summary.setter
    # def blastp_ortho_summary(self, blastp_ortho_summary):
    #     self._blastp_ortho_summary = blastp_ortho_summary
    
    # @property
    # def blastp_para_summary(self):
    #     return self._blastp_para_summary
    
    # @blastp_para_summary.setter
    # def blastp_para_summary(self, blastp_para_summary):
    #     self._blastp_para_summary = blastp_para_summary

    # @property
    # def blastp_mix_summary(self):
    #     return self._blastp_mix_summary
    
    # @blastp_mix_summary.setter
    # def blastp_mix_summary(self, blastp_mix_summary):
    #     self._blastp_mix_summary = blastp_mix_summary    
    
    # @property
    # def blastp_mix_long_summary(self):
    #     return self._blastp_mix_long_summary
    
    # @blastp_mix_long_summary.setter
    # def blastp_mix_long_summary(self, blastp_mix_long_summary):
    #     self._blastp_mix_long_summary = blastp_mix_long_summary     

    def __repr__(self):
        return self._TTHERM_ID

# functions

############# Search the TetraFGD database ##################
# search_FGD searches TetraFGD for a given TTHERM_ID 
def search_FGD(TTHERM_ID, page_num = 1):
    """ Takes TTHERM_ID (given by user) and a page number to start with

    """

    r = requests.get('http://tfgd.ihb.ac.cn/search/detail/gene/{}/page/{}'.format(TTHERM_ID, page_num))
    soup = bs4.BeautifulSoup(r.text, 'html5lib')
    title = soup.find_all('title')[0].text

    if 'TetraFGD HOME' in title:
        return soup
    elif 'TetraFGD ERROR' in title:
        print '%s was not found in the FGD' % TTHERM_ID
        return False
    elif 'Problem loading page' in title:
        print 'No internet connection. Please try again later.'
        CoregulationDataHarvester.main()

############# Search TGD Database
def search_TGD(TTHERM_ID):
    """ Same basic idea as search_FGD above.

    """

    r = requests.get('http://ciliate.org/index.php/feature/details/%s' % TTHERM_ID)
    soup = bs4.BeautifulSoup(r.text, 'html5lib')
    title = soup.find_all('title')[0].text
    if 'Gene Details' in title:
        search_result = soup

    elif 'Error Page' in title:
        # If either of the above attempts fail, this means that the gene isn't
        # listed on the TGD. In this case, we just find it on the FGD.

        # Here search result can either be True or False, depending on
        # whether the gene is listed in the FGD.
        search_result = search_FGD(TTHERM_ID)

    elif 'Problem loading page' in title:
        print 'No internet connection. Please try again.'
        CoregulationDataHarvester.main()

    return search_result




############# Record coregulated genes #################
#Generate a list of elements, each of which corresponds to a link to
#a coregulated gene.

def get_coregs_zscores_list(TTHERM_ID, threshold):
    """ Generates a list of coregulated genes, given:
        - the query TTHERM_ID (comes from user input)

        get_coregs_zscores_list calls search_FGD

        get_coregs_zscores_list returns coregs_zscores_list, which is a list
        of objects.


    """
    queried_gene = Coreg_Gene(TTHERM_ID, 'Queried Gene')
    coregs_zscores_list = [queried_gene]
    coreg_items = []
    followed_pages = {'1': 0}
    queue = ['1']
    ranout = False
    for p in queue:
        if followed_pages[p] == 0:
            followed_pages[p] = 1

            # If search worked FGDresult is a soup
            FGDresult = search_FGD(TTHERM_ID, p)
            if FGDresult == False:
                print 'Your query is not available on the FGD. Please try again with another query.'
                CoregulationDataHarvester.main()

            coreg_div = FGDresult.find_all('div', class_ = 'colist')[0]
            coregs = coreg_div.find_all('a')
            for c in coregs:
                coreg_info = c.text.split()
                ID = str(coreg_info[0])
                zscore = float(coreg_info[1])
                coreg_gene = Coreg_Gene(ID, zscore)
                coregs_zscores_list.append(coreg_gene)

            pages = FGDresult.find_all('div', class_ = 'page')[0].find_all('a')
            pages_to_follow = [str(p.text) for p in pages if p.text not in ['Next', 'Previous']]

            for p in pages_to_follow:
                if p not in followed_pages:
                    followed_pages[p] = 0
                    queue.append(p)

        else:
            continue
    
    else:
        pass
    
    # Start at -1 to account for the queried gene have a string value for its 
    # z-score
    num_genes_for_homol = -1
    for coreg_gene in coregs_zscores_list:
        if coreg_gene.zscore >= threshold:
            num_genes_for_homol += 1
        else:
            # print coreg_gene.TTHERM_ID
            break

    print
    print 'Genes co-regulated with {}: {}.'.format(TTHERM_ID, len(coregs_zscores_list))
    print 'Given the lower-bound z-score threshold of {}, the top {}'.format(threshold, num_genes_for_homol)
    print 'co-regulated genes will be subject to homology analysis.'
    print
    logging.info('Genes co-regulated with {}: {}.'.format(TTHERM_ID, len(coregs_zscores_list)))
    logging.info('Given the lower-bound z-score threshold of {}, the top {} co-regulated genes will be subject to homology analysis.'.format(threshold, num_genes_for_homol))
    return coregs_zscores_list

#### append cDNA and protein information to the coregs_zscores_list ####
def append_protein_cDNA_TGD_FGD(coregs_zscores_list):
    """ I want this function to find the cDNAs, proteins, and predicted gene
        names for each gene in my list of coregulated genes and their 
        z-scores.

        This is the more convenient place to get the predicted gene names
        because this function is already scanning TGD for each gene that I
        am interested in.

    """

    # Now need to record the FASTA DNA sequence of query so that it can be used
    # for NCBI BLAST search
    counter = 0
    for coreg_gene in coregs_zscores_list:
        # Search the TGD for each gene in coregs_zscores_list
        search_result = search_TGD(coreg_gene.TTHERM_ID)

        if search_result == True:
            # All good with the search (gene was either listed in the TGD
            # or the FGD)
            pass

        elif search_result == False:
            # All bad: gene was listed in neither the TGD nor the FGD.
            # Add meaningless descriptions and say that there is no cDNA or
            # protein sequence. Skip to the next gene in the list.
            coreg_gene.common_name = 'None'
            coreg_gene.description = 'None'

            coreg_gene.cDNA = 'FGD_cDNA: no cDNA available from FGD'
            coreg_gene.protein = 'FGD_protein: no protein available from FGD'
            continue

    # I encountered a problem where some genes listed under the FGD are not
    # listed under the TGD... In these cases, I will call search_FGD from
    # search_TGD (see the code for search_TGD above)
    # I guess I will also need to revive getting cDNA and predicted
    # gene names from search_FGD.

    # Now there are two conditions: either the gene was found in TGD, or
    # the program had to go back to FGD to find it


        try:
            # This is the case when search_TGD failed, and resorted to using
            # search_FGD
            assert 'TetraFGD HOME' in search_result.title.text
            # pdb.set_trace()

            # The FGD does not list common names 
            coreg_gene.common_name = 'None'
            coreg_gene.gene_ontology = 'No Data fetched for Gene Ontology Annotations'
            coreg_gene.description = re.sub(',', ' ', search_result.find_all('td')[1].text)

            query_cDNA_address = 'dna/locus/' + coreg_gene.TTHERM_ID
            query_protein_address = 'protein/locus/' + coreg_gene.TTHERM_ID

            FGD_cDNA_request = requests.get('http://tfgd.ihb.ac.cn/search/' + query_cDNA_address)
            FGD_cDNA_soup = bs4.BeautifulSoup(FGD_cDNA_request.text, 'html5lib')
            FGD_cDNA = FGD_cDNA_soup.find('p', class_ = 'seq').text
            if FGD_cDNA == '':
                coreg_gene.cDNA = 'FGD_cDNA: no cDNA available from FGD'
            else:
                coreg_gene.cDNA = str('FGD_cDNA: ' + FGD_cDNA)

            FGD_protein_request = requests.get('http://tfgd.ihb.ac.cn/search/' + query_protein_address)
            FGD_protein_soup = bs4.BeautifulSoup(FGD_protein_request.text, 'html5lib')
            FGD_protein = FGD_protein_soup.find('p', class_ = 'seq').text
            if FGD_protein == '':
                coreg_gene.protein = 'FGD_protein: no protein available from FGD' 
            else:
                # The protein sequence from FGD always has an asterisk at the end
                # for some reason, so I am removing it.
                coreg_gene.protein = str('FGD_protein: ' + FGD_protein[:-1])   


        except:
            #This is the case when search_TGD succeeded
            assert 'TGD' in search_result.title.text

            text = search_result.get_text()
            lines = [line.strip() for line in text.splitlines()]
            for i, l in enumerate(lines):
                if lines[i] == 'Standard Name':
                    common_name = lines[i + 1]
                if lines[i] == 'Description':
                    description = lines[i + 1]
                if lines[i] == 'Gene Ontology Annotations':
                    geneOntology = lines[i + 2]


            if description == '':
                description = 'No description available'
            coreg_gene.common_name = re.sub(
                ',', ' ', str(' '.join(common_name.encode('raw-unicode-escape').split())))

            coreg_gene.description = re.sub(
                ',', ' ', str(' '.join(description.encode('raw-unicode-escape').split())))

            coreg_gene.gene_ontology = re.sub(
                ',', ' ', str(' '.join(geneOntology.encode('raw-unicode-escape').split())))

            codes = search_result.find_all('pre')

            for code in codes:
                if 'coding' in code.text:
                    TGD_cDNA = code.text[24:]

                elif 'protein' in code.text:
                    TGD_protein = code.text[25:]

            #populate the cDNA_list, removing unicode encoding.
            coreg_gene.protein = str('TGD_protein: ' + TGD_protein)
            coreg_gene.cDNA = str('TGD_cDNA: ' + TGD_cDNA)

        counter = counter + 1

        if (counter % 10 == 0) and (counter != 0):
            print 'Collected cDNA and protein for %d genes! Still working...' % counter
            logging.info('Collected cDNA and protein for %d genes! Still working...' % counter)

    # A tool for looking through the whole list and removing entries that 
    # are missing the required information becuase the databases were lacking.
    # The assumption right now is that we should always remove the gene, if
    # either cDNA or protein data is missing.

    # I encountered a bug where if there were two genes with missing sequences
    # in a row, my old way of doing it would skip removing the second gene.
    # To fix this, I'm taking a two-step apporach: first find all the indices
    # of gene information lists that are missing cDNA or protein sequences
    # and put them into seqRemovalList. Then, using this list, use pop() to
    # actually remove the offensive things.

    seqRemovalList = []
    for coreg_gene in coregs_zscores_list:
        if 'no cDNA available' in coreg_gene.cDNA:
            print 'There was no cDNA sequence available for %s' \
                % coreg_gene.TTHERM_ID

            logging.info('There was no cDNA sequence available for %s' \
                % coreg_gene.TTHERM_ID)
            seqRemovalList.append(coregs_zscores_list.index(coreg_gene))

        if 'no protein available' in coreg_gene.protein:
            print 'There was no protein sequence available for %s' \
                % coreg_gene.TTHERM_ID

            logging.info('There was no protein sequence available for %s' \
                % coreg_gene.TTHERM_ID)

    # Reverse seqRemovalList so that things don't get weird with indices
    # changing with the length of coregs_zscores_list changing while
    # entries are removed.

    seqRemovalList.reverse()

    for i in seqRemovalList:
        print 'Removing %s from the list' % coregs_zscores_list[i].TTHERM_ID
        logging.info('Removing %s from the list' % coregs_zscores_list[i].TTHERM_ID)
        coregs_zscores_list.pop(i)


    return coregs_zscores_list

# set intersections:

def coreg_intersection(list_of_coreg_lists):
    # pdb.set_trace()
    if len(list_of_coreg_lists) == 1:
        coregs_zscores_cDNA_list = list_of_coreg_lists[0]
    else:
        text_lists = []
        for l in list_of_coreg_lists:
            text_lists.append(map(str, l))
        text_cross_set = set.intersection(*map(set, text_lists))
        gene_obj_cross_list = []
        for l in list_of_coreg_lists:
            for g in l:
                if g.TTHERM_ID in text_cross_set:
                    gene_obj_cross_list.append(g)
        
        g_removal_list = []
        dict_of_ttherms = {}
        for g in gene_obj_cross_list:
            dict_of_ttherms[g.TTHERM_ID] = dict_of_ttherms.get(g.TTHERM_ID, 0) + 1
        for key, val in dict_of_ttherms.items():
            if val > 1:
                for g in gene_obj_cross_list[::-1]:
                    if val != 1:
                        if g.TTHERM_ID == key:
                            g_removal_list.append(gene_obj_cross_list.index(g))
                            val -= 1
        g_removal_list.sort()
        g_removal_list.reverse()
        # pdb.set_trace()
        for i in g_removal_list:
            gene_obj_cross_list.pop(i)

        coregs_zscores_cDNA_list = gene_obj_cross_list
        # pdb.set_trace()

    return coregs_zscores_cDNA_list


################ Driving the web searches and forward blasts ##############

def WebMod(formatted_TTHERM_ID_list, threshold, owOption, 
    syncOption, blastOption, entrez, clade):
    """ Takes searchInput (formatted_TTHERM_ID_list) and threshold (the lower-bound for
        z-scores that we are interested in), as well as the user-defined 
        (in the CoregulationDataHarvester Module) overwrite option (owOption),
        synchronization option (syncOption), BLAST option (blastOption),
        entrez coded (entrez), and phrase for file naming (clade).
        Makes sure that everything is formatted properly.

        Runs get_coregs_zscores_list, append_cDNA_TGD_FGD, and NCBI_qBLAST
        
    """
    pickle_address, drop_pickle_address = filename_generator.filename_generator('coregs_zscores', formatted_TTHERM_ID_list)
    # less convenient to put in to filename generator than here
    if platform.system() == 'Darwin':
        drop_pickle_dir_address = os.path.expanduser(
            r'~/Dropbox/CoregulationDataHarvester/pickledData')
    elif platform.system() == 'Windows':
        drop_pickle_dir_address = os.path.join(
            shell.SHGetFolderPath(
                0, shellcon.CSIDL_PROFILE, None, 0),
            r'Dropbox/CoregulationDataHarvester/pickledData/')
 
    elif platform.system() == 'Linux':
        drop_pickle_dir_address = os.path.expanduser(
            r'~/Dropbox/CoregulationDataHarvester/pickledData')

    # # Initialize pickleData folder, if needed
    # # Since I want to centralize everything through Dropbox, I really don't 
    # # anyone messing with the folders. The program assumes that if you are
    # # using Dropbox, then you have synced according to my instructions
    # if not os.path.exists(pickle_dir_address):
    #     os.makedirs(pickle_dir_address)

    if syncOption != 3 and not os.path.exists(drop_pickle_dir_address):
        print
        print 'It seems that your Dropbox is not synced to the Coregulation '\
            'Data Harvester.'
        print 'Please sync before trying again.'
        CoregulationDataHarvester.main()

    # Check if coregs_zscores_cDNA_list has already been pickled/overwrite
    # if user so desires :
    if owOption == 1:

        print 'Search initialized with query:', formatted_TTHERM_ID_list
        logging.info('Search initialized with query: {}'.format(formatted_TTHERM_ID_list))

        # for cross analysis
        list_of_coreg_lists = []
        for ttherm in formatted_TTHERM_ID_list:

            coregs_zscores_list = get_coregs_zscores_list(ttherm, threshold)
            coregs_zscores_cDNA_list = append_protein_cDNA_TGD_FGD(
                coregs_zscores_list)
            list_of_coreg_lists.append(coregs_zscores_cDNA_list)
        #pdb.set_trace()
        
        coregs_zscores_cDNA_list = coreg_intersection(list_of_coreg_lists)
        # Write both to Dropbox and locally
        if syncOption == 1:
            drop_pickle_f = open(drop_pickle_address, 'wb')
            dill.dump(coregs_zscores_cDNA_list, drop_pickle_f)
            drop_pickle_f.close()

            pickle_f = open(pickle_address, 'wb')
            dill.dump(coregs_zscores_cDNA_list, pickle_f)
            pickle_f.close()         

        # Write only to Dropbox
        elif syncOption == 2:
            drop_pickle_f = open(drop_pickle_address, 'wb')
            dill.dump(coregs_zscores_cDNA_list, drop_pickle_f)
            drop_pickle_f.close()

        # Write only locally
        elif syncOption == 3:
            pickle_f = open(pickle_address, 'wb')
            dill.dump(coregs_zscores_cDNA_list, pickle_f)
            pickle_f.close()

        BLASTmod.NCBI_qBLAST(
            coregs_zscores_cDNA_list, formatted_TTHERM_ID_list, owOption, 
            blastOption, syncOption, entrez, clade, threshold)


    # In this case might only need to overwrite BLAST searches
    elif owOption == 2 or owOption == 3:
        # pdb.set_trace()
        
        # Here user wants to make use of Dropbox
        # The question becomes where to pull existing data from.

        if syncOption != 3:
            # Case when needed file exists in neither Dropbox nor local dir:
            # Complain, ask if user wants to proceed by starting with fresh
            # TGD/FGD search
            if not os.path.exists(drop_pickle_address) and\
                not os.path.exists(pickle_address):
                print 'You opted to use an existing FGD/TGD for your analysis'
                print 'but the data file does not exist in either your'
                print 'Dropbox folder or your local folder.'
                print

                contChoice = raw_input(
                    '''Do you want to start this query from the TGD/FGD search
(y: proceed, and still try to reuse previous BLAST results. n: restart)? ''').lower()[0]
                if contChoice == 'y':
                    # Behave like owOption == 1:
                    print
                    print 'Search initialized with query:', formatted_TTHERM_ID_list
                    logging.info('Search initialized with query: {}'.format(formatted_TTHERM_ID_list))

                    #search_FGD(TTHERM_ID, browser)
                    # for cross analysis
                    list_of_coreg_lists = []
                    for ttherm in formatted_TTHERM_ID_list:

                        coregs_zscores_list = get_coregs_zscores_list(ttherm, threshold)
                        coregs_zscores_cDNA_list = append_protein_cDNA_TGD_FGD(
                            coregs_zscores_list)
                        list_of_coreg_lists.append(coregs_zscores_cDNA_list)
                    
                    coregs_zscores_cDNA_list = coreg_intersection(list_of_coreg_lists)

                    # Write both to Dropbox and locally
                    if syncOption == 1:
                        drop_pickle_f = open(drop_pickle_address, 'wb')
                        dill.dump(coregs_zscores_cDNA_list, drop_pickle_f)
                        drop_pickle_f.close()

                        pickle_f = open(pickle_address, 'wb')
                        dill.dump(coregs_zscores_cDNA_list, pickle_f)
                        pickle_f.close()         

                    # Write only to Dropbox
                    elif syncOption == 2:
                        drop_pickle_f = open(drop_pickle_address, 'wb')
                        dill.dump(coregs_zscores_cDNA_list, drop_pickle_f)
                        drop_pickle_f.close()


                    BLASTmod.NCBI_qBLAST(
                        coregs_zscores_cDNA_list, formatted_TTHERM_ID_list, owOption, 
                        blastOption, syncOption, entrez, clade, threshold)

                elif contChoice == 'n':
                    print
                    CoregulationDataHarvester.main()
            
            # Case when needed file is in Dropbox, but not locally:
            # Use Dropbox file and copy it to the local machine
            elif os.path.exists(drop_pickle_address) and\
                not os.path.exists(pickle_address):
                print 'FGD/TGD search exists in Dropbox, but not locally'
                print 'Writing FGD/TGD search from Dropbox to local directory'
                print
                logging.info('FGD/TGD search exists in Dropbox, but not locally')
                logging.info('Writing FGD/TGD search from Dropbox to local directory')
                
                src = drop_pickle_address
                dst = pickle_address
                shutil.copy2(src, dst)

                print 'Initializing using the FGD/TGD search stored in Dropbox'
                logging.info('Initializing using the FGD/TGD search stored in Dropbox')
                print
                coregs_zscores_cDNA_list_file = open(drop_pickle_address, 'rb')
                coregs_zscores_cDNA_list = dill.load(
                    coregs_zscores_cDNA_list_file)
                coregs_zscores_cDNA_list_file.close()
                BLASTmod.NCBI_qBLAST(coregs_zscores_cDNA_list, formatted_TTHERM_ID_list, owOption, 
                    blastOption, syncOption, entrez, clade, threshold)
                
            
            # Case when needed file is present locally, but not in Dropbox:
            # Use local file, and copy it to Dropbox
            elif not os.path.exists(drop_pickle_address) and \
                os.path.exists(pickle_address):
                print 'FGD/TGD search exists locally, but not in Dropbox'
                print 'Writing FGD/TGD search from local directory to Dropbox'
                print
                logging.info('FGD/TGD search exists locally, but not in Dropbox')
                logging.info('Writing FGD/TGD search from local directory to Dropbox')
                src = pickle_address
                dst = drop_pickle_address
                shutil.copy2(src, dst)

                print 'Initializing using the FGD/TGD search stored locally'
                logging.info('Initializing using the FGD/TGD search stored locally')
                print
                coregs_zscores_cDNA_list_file = open(pickle_address, 'rb')
                coregs_zscores_cDNA_list = dill.load(
                    coregs_zscores_cDNA_list_file)
                coregs_zscores_cDNA_list_file.close()

                BLASTmod.NCBI_qBLAST(coregs_zscores_cDNA_list, formatted_TTHERM_ID_list, owOption, 
                    blastOption, syncOption, entrez, clade, threshold)

            # Case when the needed file is present both locally and in Dropbox
            # Here, because I would rather every file be synchronized than
            # necessarily be the most current, the program uses the Dropbox 
            # file and overwrites the local one.
            elif os.path.exists(drop_pickle_address) and \
                os.path.exists(pickle_address):
                print 'FGD/TGD search exists both locally and in Dropbox'
                print 'Writing FGD/TGD search from Dropbox to local directory'
                print
                logging.info('FGD/TGD search exists both locally and in Dropbox')
                logging.info('Writing FGD/TGD search from Dropbox to local directory')
                src = drop_pickle_address
                dst = pickle_address
                shutil.copy2(src, dst)

                print 'Initializing using the FGD/TGD search stored in Dropbox'
                logging.info('Initializing using the FGD/TGD search stored in Dropbox')
                print
                coregs_zscores_cDNA_list_file = open(drop_pickle_address, 'rb')
                coregs_zscores_cDNA_list = dill.load(
                    coregs_zscores_cDNA_list_file)
                coregs_zscores_cDNA_list_file.close()
                BLASTmod.NCBI_qBLAST(coregs_zscores_cDNA_list, formatted_TTHERM_ID_list, owOption, 
                    blastOption, syncOption, entrez, clade, threshold)


        # Here the user wants to run the program locally. This is just as it
        # was before implementing dropbox syncing
        elif syncOption == 3:
            if not os.path.exists(pickle_address):
                print 'You opted to use an existing FGD/TGD for your analysis'
                print 'but the data file does not exist in either your'
                print 'Dropbox folder or your local folder.'
                print

                contChoice = raw_input(
                    '''Do you want to start this query from the TGD/FGD search
(y: proceed, and still try to reuse previous BLAST results. n: restart)? ''').lower()[0]
                if contChoice == 'y':
                    # Behave like owOption == 1:
                    print
                    print 'Search initialized with query:', formatted_TTHERM_ID_list
                    logging.info('Search initialized with query: {}'.format(formatted_TTHERM_ID_list))
        
                    # for cross analysis
                    list_of_coreg_lists = []
                    for ttherm in formatted_TTHERM_ID_list:

                        coregs_zscores_list = get_coregs_zscores_list(ttherm, threshold)
                        coregs_zscores_cDNA_list = append_protein_cDNA_TGD_FGD(
                            coregs_zscores_list)
                        list_of_coreg_lists.append(coregs_zscores_cDNA_list)
                    
                    coregs_zscores_cDNA_list = coreg_intersection(list_of_coreg_lists)

                    # Write only locally
                    pickle_f = open(pickle_address, 'wb')
                    dill.dump(coregs_zscores_cDNA_list, pickle_f)
                    pickle_f.close()
                    # pdb.set_trace()
                    BLASTmod.NCBI_qBLAST(
                        coregs_zscores_cDNA_list, formatted_TTHERM_ID_list, owOption, 
                        blastOption, syncOption, entrez, clade, threshold)

                elif contChoice == 'n':
                    print
                    CoregulationDataHarvester.main()
            else:
                # print 'should redo the NCBI blasts'
                # pdb.set_trace()
                coregs_zscores_cDNA_list_file = open(pickle_address, 'rb')
                coregs_zscores_cDNA_list = dill.load(
                    coregs_zscores_cDNA_list_file)
                coregs_zscores_cDNA_list_file.close()
                BLASTmod.NCBI_qBLAST(
                    coregs_zscores_cDNA_list, formatted_TTHERM_ID_list, owOption, 
                    blastOption, syncOption, entrez, clade, threshold)

    elif owOption == 5:
        print 'FGD/TGD search initialized with query:', formatted_TTHERM_ID_list
        logging.info('FGD/TGD search initialized with query: {}'.format(formatted_TTHERM_ID_list))

        # for cross analysis
        list_of_coreg_lists = []
        for ttherm in formatted_TTHERM_ID_list:

            coregs_zscores_list = get_coregs_zscores_list(ttherm, threshold)
            coregs_zscores_cDNA_list = append_protein_cDNA_TGD_FGD(
                coregs_zscores_list)
            list_of_coreg_lists.append(coregs_zscores_cDNA_list)
        
        coregs_zscores_cDNA_list = coreg_intersection(list_of_coreg_lists)

        # Write both to Dropbox and locally
        if syncOption == 1:
            drop_pickle_f = open(drop_pickle_address, 'wb')
            dill.dump(coregs_zscores_cDNA_list, drop_pickle_f)
            drop_pickle_f.close()

            pickle_f = open(pickle_address, 'wb')
            dill.dump(coregs_zscores_cDNA_list, pickle_f)
            pickle_f.close()         

        # Write only to Dropbox
        elif syncOption == 2:
            drop_pickle_f = open(drop_pickle_address, 'wb')
            dill.dump(coregs_zscores_cDNA_list, drop_pickle_f)
            drop_pickle_f.close()

        # Write only locally
        elif syncOption == 3:
            pickle_f = open(pickle_address, 'wb')
            dill.dump(coregs_zscores_cDNA_list, pickle_f)
            pickle_f.close()

    return


if (__name__ == '__main__'):
    import doctest
    doctest.testmod()


    