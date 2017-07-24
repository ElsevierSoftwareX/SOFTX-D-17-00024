#!/usr/bin/python

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
__version__ = '1.2.0'

# imports
import sys
import os
import traceback
import time
import platform
import pdb
import shutil
import CoregulationDataHarvester
import requests
import bs4
from Bio.Blast import NCBIWWW
from Bio.Blast import NCBIXML
from Bio import Entrez
import xml.etree.ElementTree as ET
import re
import difflib
import logging
import filename_generator

if platform.system() == 'Windows':
    from win32com.shell import shell, shellcon

# Let NCBI know who is responsible for all the requests
Entrez.email = 'coregulationdataharvester@gmail.com'

# function to account for cross-analyses
def to_blast(coregs_zscores_cDNA_list, formatted_TTHERM_ID_list, threshold):
    toBLAST = []
    if len(formatted_TTHERM_ID_list) == 1:
        for g in coregs_zscores_cDNA_list:
            if g.zscore >= threshold:
                    
                toBLAST.append(g)
    
    else:
        for g in coregs_zscores_cDNA_list:
            if (g.zscore >= threshold) or (g.TTHERM_ID in formatted_TTHERM_ID_list):
                    
                toBLAST.append(g)

    # pdb.set_trace()
    return toBLAST



# Runs the BLAST searches for each gene in the co-regulated set
def NCBI_qBLAST(coregs_zscores_cDNA_list, formatted_TTHERM_ID_list, owOption, 
    blastOption, syncOption, entrez, clade, threshold):
    """ This fundtion calls NCBIWWW.qblast() from the biopython module.
        I am giving it the following parameters:
            - blast(p/x): protein or cDNA blast using translated nucleotide
              query
            - nr: non-redundant protein sequences
            - cDNA or protein from my coregs_zscores_cDNA_list
            - genetic_code = 'Ciliate Nuclear' for proper translation if using
              cDNA
            - entrez_query = 'NOT Ciliata', 'Ciliata NOT Tetrahymena thermophila
            [Orgn]', '(none)', or custom-defined

        This function writes all the results from the blasting to .XML files.
        Each file is formatted TTHERM_ID_clade_blast(p/x).XML (where clade 
        depends on entrez as defined in the master module). My hope is
        that is naming scheme will make it easy to process data from the files
        using regular expressions, as well as easily readable and understanble 
        to the human eye.
    """

    print 'Initializing BLAST API: This may take some time...'

    # Run blasts for all sequences that are available, take a minute break for every 25
    # BLASTs performed so that the NCBI is less like to get angry
    BLASTs_performed = 1
    toBLAST = to_blast(coregs_zscores_cDNA_list, formatted_TTHERM_ID_list, threshold)

    # print 'here'
    # pdb.set_trace()
    
    for coreg_gene in toBLAST:

        if (BLASTs_performed % 25) == 0:
            print
            print "Giving the NCBI a minute's rest."
            time.sleep(60)
            print "Moving on..."
            print

        # Run BLAST before opening file so that if program is
        # interrupted, it is less likely that the directory is polluted
        # with empty files.
        # the reciprocal addresses here are wasted
        xf_address, drop_xf_address, reciprocal_blastx_address, drop_reciprocal_blastx_address = \
        filename_generator.filename_generator('blast', [coreg_gene.TTHERM_ID], clade = clade, blastOption = 'blastx')

        pf_address, drop_pf_address, reciprocal_blastp_address, drop_reciprocal_blastp_address = \
        filename_generator.filename_generator('blast', [coreg_gene.TTHERM_ID], clade = clade, blastOption = 'blastp')
        # Case when user wants all BLAST results overwritten
        if owOption != 3:
            if blastOption == 'blastx':
                xblast_result_handle = NCBIWWW.qblast("blastx", "nr", 
                    coreg_gene.cDNA[10:],
                    genetic_code = 'Ciliate Nuclear',
                    entrez_query = entrez)
                BLASTs_performed += 1

                if not xblast_result_handle:
                    print 'BLASTx for %s failed. Skipping...' % coreg_gene.TTHERM_ID
                    logging.info('BLASTx for %s failed. Skipping...' % coreg_gene.TTHERM_ID)
                    break

                else:
                    # This is the case when the BLAST was successful
                    xblast_result = xblast_result_handle.read()

                # Write both locally and to Dropbox
                if syncOption == 1:
                    drop_xf = open(drop_xf_address, 'wb')
                    drop_xf.write(xblast_result)
                    drop_xf.close()
                    print 'Dropbox BLASTx profile for %s complete' \
                        % coreg_gene.TTHERM_ID
                    logging.info('Dropbox BLASTx profile for %s complete' \
                        % coreg_gene.TTHERM_ID)

                    xf = open(xf_address, 'wb')
                    xf.write(xblast_result)
                    xf.close()
                    print 'Local BLASTx profile for %s complete' \
                        % coreg_gene.TTHERM_ID
                    logging.info('Local BLASTx profile for %s complete' \
                        % coreg_gene.TTHERM_ID)

                # Write only to Dropbox
                elif syncOption == 2:
                    drop_xf = open(drop_xf_address, 'wb')
                    drop_xf.write(xblast_result)
                    drop_xf.close()
                    print 'Dropbox BLASTx profile for %s complete' \
                        % coreg_gene.TTHERM_ID
                    logging.info('Dropbox BLASTx profile for %s complete' \
                        % coreg_gene.TTHERM_ID)                    

                # Write only locally
                elif syncOption == 3:
                    xf = open(xf_address, 'wb')
                    xf.write(xblast_result)
                    xf.close()
                    print 'Local BLASTx profile for %s complete' \
                        % coreg_gene.TTHERM_ID
                    logging.info('Local BLASTx profile for %s complete' \
                        % coreg_gene.TTHERM_ID)

            elif blastOption == 'blastp':
                pblast_result_handle = NCBIWWW.qblast("blastp", "nr", 
                    coreg_gene.protein[13:],
                    entrez_query = entrez)
                BLASTs_performed += 1

                if not pblast_result_handle:
                    print 'BLASTp for %s failed. Skipping...' % coreg_gene.TTHERM_ID
                    logging.info('BLASTp for %s failed. Skipping...' % coreg_gene.TTHERM_ID)
                    break

                else:
                    # This is the case when BLAST was successful
                    pblast_result = pblast_result_handle.read()

                # Write both locally and to Dropbox
                if syncOption == 1:
                    drop_pf = open(drop_pf_address, 'wb')
                    drop_pf.write(pblast_result)
                    drop_pf.close()
                    print 'Dropbox BLASTp profile for %s complete' \
                        % coreg_gene.TTHERM_ID
                    logging.info('Dropbox BLASTp profile for %s complete' \
                        % coreg_gene.TTHERM_ID)

                    pf = open(pf_address, 'wb')
                    pf.write(pblast_result)
                    pf.close()
                    print 'Local BLASTp profile for %s complete' \
                        % coreg_gene.TTHERM_ID
                    logging.info('Local BLASTp profile for %s complete' \
                        % coreg_gene.TTHERM_ID)

                # Write only to Dropbox
                if syncOption == 2:
                    drop_pf = open(drop_pf_address, 'wb')
                    drop_pf.write(pblast_result)
                    drop_pf.close()
                    print 'Dropbox BLASTp profile for %s complete' \
                        % coreg_gene.TTHERM_ID
                    logging.info('Dropbox BLASTp profile for %s complete' \
                        % coreg_gene.TTHERM_ID)

                # Write only locally
                if syncOption == 3:
                    # print 'about to write blast file'
                    # pdb.set_trace()
                    pf = open(pf_address, 'wb')
                    pf.write(pblast_result)
                    pf.close()
                    print 'Local BLASTp profile for %s complete' \
                        % coreg_gene.TTHERM_ID
                    logging.info('Local BLASTp profile for %s complete' \
                        % coreg_gene.TTHERM_ID)

            elif blastOption == 'both':

                # First run BLAST
                xblast_result_handle = NCBIWWW.qblast("blastx", "nr", 
                    coreg_gene.cDNA[10:],
                    genetic_code = 'Ciliate Nuclear',
                    entrez_query = entrez)
                BLASTs_performed += 1

                if not xblast_result_handle:
                    print 'BLASTx for %s failed. Skipping...'
                    logging.info('BLASTx for %s failed. Skipping...')
                    break

                else:
                    # This is the case when BLAST was successful
                    xblast_result = xblast_result_handle.read()

                # Then run BLASTp
                pblast_result_handle = NCBIWWW.qblast("blastp", "nr", 
                    coreg_gene.protein[13:],
                    entrez_query = entrez)
                BLASTs_performed += 1

                if not pblast_result_handle:
                    print 'BLASTp for %s failed. Skipping...'
                    logging.info('BLASTp for %s failed. Skipping...')
                    break

                else:
                    # This is the case when BLAST was successful
                    pblast_result = pblast_result_handle.read()

                # Write both locally and to Dropbox
                if syncOption == 1:
                    # Write BLASTx results...
                    # ... to Dropbox
                    drop_xf = open(drop_xf_address, 'wb')
                    drop_xf.write(xblast_result)
                    drop_xf.close()
                    print 'Dropbox BLASTx profile for %s complete' \
                        % coreg_gene.TTHERM_ID
                    logging.info('Dropbox BLASTx profile for %s complete' \
                        % coreg_gene.TTHERM_ID)

                    # ... and locally
                    xf = open(xf_address, 'wb')
                    xf.write(xblast_result)
                    xf.close()
                    print 'Local BLASTx profile for %s complete' \
                        % coreg_gene.TTHERM_ID
                    logging.info('Local BLASTx profile for %s complete' \
                        % coreg_gene.TTHERM_ID)
                    
                    # Write BLASTp results...
                    # ... to Dropbox
                    drop_pf = open(drop_pf_address, 'wb')
                    drop_pf.write(pblast_result)
                    drop_pf.close()
                    print 'Dropbox BLASTp profile for %s complete' \
                        % coreg_gene.TTHERM_ID
                    logging.info('Dropbox BLASTp profile for %s complete' \
                        % coreg_gene.TTHERM_ID)
                    
                    # ... and locally
                    pf = open(pf_address, 'wb')
                    pf.write(pblast_result)
                    pf.close()
                    print 'Local BLASTp profile for %s complete' \
                        % coreg_gene.TTHERM_ID
                    logging.info('Local BLASTp profile for %s complete' \
                        % coreg_gene.TTHERM_ID)
                
                # Write only to Dropbox
                elif syncOption == 2:
                    # Write BLASTx results
                    drop_xf = open(drop_xf_address, 'wb')
                    drop_xf.write(xblast_result)
                    drop_xf.close()
                    print 'Dropbox BLASTx profile for %s complete' \
                        % coreg_gene.TTHERM_ID 
                    logging.info('Dropbox BLASTx profile for %s complete' \
                        % coreg_gene.TTHERM_ID) 

                    # Write BLASTp results
                    drop_pf = open(drop_pf_address, 'wb')
                    drop_pf.write(pblast_result)
                    drop_pf.close()
                    print 'Dropbox BLASTp profile for %s complete' \
                        % coreg_gene.TTHERM_ID 
                    logging.info('Dropbox BLASTp profile for %s complete' \
                        % coreg_gene.TTHERM_ID )                 

                # Write only locally
                elif syncOption == 3:
                    # Write BLASTx results
                    xf = open(xf_address, 'wb')
                    xf.write(xblast_result)
                    xf.close()
                    print 'Local BLASTx profile for %s complete' \
                        % coreg_gene.TTHERM_ID
                    logging.info('Local BLASTx profile for %s complete' \
                        % coreg_gene.TTHERM_ID)

                    # Write BLASTp results
                    pf = open(pf_address, 'wb')
                    pf.write(pblast_result)
                    pf.close()
                    print 'Local BLASTp profile for %s complete' \
                        % coreg_gene.TTHERM_ID
                    logging.info('Local BLASTp profile for %s complete' \
                        % coreg_gene.TTHERM_ID)

        # Case when user wants to only write new BLAST results, and not 
        # overwrite already existing BLAST searches
        elif owOption == 3:
            # pdb.set_trace()

            if blastOption == 'blastx':
                # Case when user wants both Dropbox and local files
                # I do this for both syncOption == 1 or syncOption == 2 because
                # this should add speed if someone already ran the search to
                # Dropbox, which is one of my ultimate goals
                if syncOption != 3:
                    # Case when neither Dropbox nor local file exists:
                    # Write both!
                    if not os.path.exists(xf_address) and \
                        not os.path.exists(drop_xf_address):

                        xblast_result_handle = NCBIWWW.qblast("blastx", "nr", 
                            coreg_gene.cDNA[10:],
                            genetic_code = 'Ciliate Nuclear',
                            entrez_query = entrez)
                        BLASTs_performed += 1

                        if not xblast_result_handle:
                            print 'BLASTx for %s failed. Skipping...' \
                                % coreg_gene.TTHERM_ID
                            logging.info('BLASTx for %s failed. Skipping...' \
                                % coreg_gene.TTHERM_ID)
                            break
                        else:
                            # This is the case when BLAST was successful
                            xblast_result = xblast_result_handle.read()

                        xf = open(xf_address, 'wb')
                        xf.write(xblast_result)
                        xf.close()
                        print 'Local BLASTx profile for %s complete' \
                            % coreg_gene.TTHERM_ID
                        logging.info('Local BLASTx profile for %s complete' \
                            % coreg_gene.TTHERM_ID)

                        drop_xf = open(drop_xf_address, 'wb')
                        drop_xf.write(xblast_result)
                        drop_xf.close()
                        print 'Dropbox BLASTx profile for %s complete' \
                            % coreg_gene.TTHERM_ID
                        logging.info('Dropbox BLASTx profile for %s complete' \
                            % coreg_gene.TTHERM_ID)

                    # Case when Dropbox file exists, but local does not:
                    # Copy Dropbox file to local directory!
                    # I am prioritizing keeping the Dropbox and local files
                    # equivalent over necessarily having the most current file
                    elif not os.path.exists(xf_address) and \
                        os.path.exists(drop_xf_address):

                        src = drop_xf_address
                        dst = xf_address

                        shutil.copy2(src, dst)
                        print 'Copied Dropbox BLASTx profile for %s to the ' \
                            'local folder.' % coreg_gene.TTHERM_ID
                        logging.info('Copied Dropbox BLASTx profile for %s to the ' \
                            'local folder.' % coreg_gene.TTHERM_ID)

                    # Case when local file exists, but the Dropbox one does not
                    # Reverse of case immediately above
                    elif os.path.exists(xf_address) and \
                        not os.path.exists(drop_xf_address):

                        src = xf_address
                        dst = drop_xf_address

                        shutil.copy2(src, dst)
                        print 'Copied local BLASTx profile for %s to the ' \
                            'Dropbox folder.' % coreg_gene.TTHERM_ID
                        logging.info('Copied local BLASTx profile for %s to the ' \
                            'Dropbox folder.' % coreg_gene.TTHERM_ID)

                    # Case when both local and Dropbox files exist:
                    # leave everything as is!
                    elif os.path.exists(xf_address) and \
                        os.path.exists(drop_xf_address):

                        print 'Both the local and Dropbox BLASTx profiles ' \
                            'for %s already exist' % coreg_gene.TTHERM_ID
                        logging.info('Both the local and Dropbox BLASTx profiles ' \
                            'for %s already exist' % coreg_gene.TTHERM_ID)

                # Here the user only wants local files, so we can keep the 
                # same approach as before Dropbox integration
                elif syncOption == 3:
                    if not os.path.exists(xf_address):
                        xblast_result_handle = NCBIWWW.qblast("blastx", "nr", 
                            coreg_gene.cDNA[10:],
                            genetic_code = 'Ciliate Nuclear',
                            entrez_query = entrez)
                        BLASTs_performed += 1

                        if not xblast_result_handle:
                            print 'BLASTx for %s failed. Skipping...' \
                                % coreg_gene.TTHERM_ID
                            logging.info('BLASTx for %s failed. Skipping...' \
                                % coreg_gene.TTHERM_ID)
                            break

                        else:
                            # This is the case when BLAST was successful
                            xblast_result = xblast_result_handle.read()

                        xf = open(xf_address, 'wb')
                        xf.write(xblast_result)
                        xf.close()
                        print 'Local BLASTx profile for %s complete' \
                            % coreg_gene.TTHERM_ID
                        logging.info('Local BLASTx profile for %s complete' \
                            % coreg_gene.TTHERM_ID)

                    else:
                        print 'The local BLASTx profile for %s already exists'\
                            % coreg_gene.TTHERM_ID
                        logging.info('The local BLASTx profile for %s already exists'\
                            % coreg_gene.TTHERM_ID)

            elif blastOption == 'blastp':

                # Case when user wants both Dropbox and local files
                # I do this for both syncOption == 1 or syncOption == 2 because
                # this should add speed if someone already ran the search to
                # Dropbox, which is one of my ultimate goals
                if syncOption != 3:
                    # Case when neither Dropbox nor local file exists:
                    # Write both!
                    if not os.path.exists(pf_address) and \
                        not os.path.exists(drop_pf_address):

                        pblast_result_handle = NCBIWWW.qblast("blastp", "nr", 
                            coreg_gene.protein[13:],
                            entrez_query = entrez)
                        BLASTs_performed += 1

                        if not pblast_result_handle:
                            print 'BLASTp for %s failed. Skipping...' \
                                % coreg_gene.TTHERM_ID
                            logging.info('BLASTp for %s failed. Skipping...' \
                                % coreg_gene.TTHERM_ID)
                            break

                        else:
                            # This is the case when BLAST was successful
                            pblast_result = pblast_result_handle.read()
                        
                        pf = open(pf_address, 'wb')
                        pf.write(pblast_result)
                        pf.close()
                        print 'Local BLASTp profile for %s complete' \
                            % coreg_gene.TTHERM_ID
                        logging.info('Local BLASTp profile for %s complete' \
                            % coreg_gene.TTHERM_ID)

                        drop_pf = open(drop_pf_address, 'wb')
                        drop_pf.write(pblast_result)
                        drop_pf.close()
                        print 'Dropbox BLASTp profile for %s complete' \
                            % coreg_gene.TTHERM_ID
                        logging.info('Dropbox BLASTp profile for %s complete' \
                            % coreg_gene.TTHERM_ID)

                    # Case when Dropbox file exists, but local does not:
                    # Copy Dropbox file to local directory!
                    # I am prioritizing keeping the Dropbox and local files
                    # equivalent over necessarily having the most current file
                    elif not os.path.exists(pf_address) and \
                        os.path.exists(drop_pf_address):

                        src = drop_pf_address
                        dst = pf_address

                        shutil.copy2(src, dst)
                        print 'Copied Dropbox BLASTp profile for %s to the ' \
                            'local folder.' % coreg_gene.TTHERM_ID
                        logging.info('Copied Dropbox BLASTp profile for %s to the ' \
                            'local folder.' % coreg_gene.TTHERM_ID)

                    # Case when local file exists, but the Dropbox one does not
                    # Reverse of case immediately above
                    elif os.path.exists(pf_address) and \
                        not os.path.exists(drop_pf_address):

                        src = pf_address
                        dst = drop_pf_address

                        shutil.copy2(src, dst)
                        print 'Copied local BLASTp profile for %s to the ' \
                            'Dropbox folder.' % coreg_gene.TTHERM_ID
                        logging.info('Copied local BLASTp profile for %s to the ' \
                            'Dropbox folder.' % coreg_gene.TTHERM_ID)

                    # Case when both local and Dropbox files exist:
                    # leave everything as is!
                    elif os.path.exists(pf_address) and \
                        os.path.exists(drop_pf_address):

                        print 'Both the local and Dropbox BLASTp profiles ' \
                            'for %s already exist' % coreg_gene.TTHERM_ID
                        logging.info('Both the local and Dropbox BLASTp profiles ' \
                            'for %s already exist' % coreg_gene.TTHERM_ID)

                # Here, the user wants nothing to do with Dropbox, so we can
                # keep things as before Dropbox integration
                elif syncOption == 3:
                    if not os.path.exists(pf_address):
                        pblast_result_handle = NCBIWWW.qblast("blastp", "nr", 
                            coreg_gene.protein[13:],
                            entrez_query = entrez)
                        BLASTs_performed += 1

                        if not pblast_result_handle:
                            print 'BLASTp for %s failed. Skipping...' \
                                % coreg_gene.TTHERM_ID
                            logging.info('BLASTp for %s failed. Skipping...' \
                                % coreg_gene.TTHERM_ID)
                            break

                        else:
                            # This is the case when BLAST was successful
                            pblast_result = pblast_result_handle.read()

                        pf = open(pf_address, 'wb')
                        pf.write(pblast_result)
                        pf.close()
                        # print 'here'
                        # pdb.set_trace()
                        print 'Local BLASTp profile for %s complete' \
                            % coreg_gene.TTHERM_ID
                        logging.info('Local BLASTp profile for %s complete' \
                            % coreg_gene.TTHERM_ID)

                    else:
                        print 'The local BLASTp profile for %s already exists'\
                            % coreg_gene.TTHERM_ID
                        logging.info('The local BLASTp profile for %s already exists'\
                            % coreg_gene.TTHERM_ID)

            elif blastOption == 'both':
                # pdb.set_trace()
                # First run BLASTx...
                # Case when user wants both Dropbox and local files
                # I do this for both syncOption == 1 or syncOption == 2 because
                # this should add speed if someone already ran the search to
                # Dropbox, which is one of my ultimate goals
                if syncOption != 3:
                    # Case when neither Dropbox nor local file exists:
                    # Write both!
                    if not os.path.exists(xf_address) and \
                        not os.path.exists(drop_xf_address):

                        xblast_result_handle = NCBIWWW.qblast("blastx", "nr", 
                            coreg_gene.cDNA[10:],
                            genetic_code = 'Ciliate Nuclear',
                            entrez_query = entrez)
                        BLASTs_performed += 1

                        if not xblast_result_handle:
                            print 'BLASTx for %s failed. Skipping...' \
                                % coreg_gene.TTHERM_ID
                            logging.info('BLASTx for %s failed. Skipping...' \
                                % coreg_gene.TTHERM_ID)
                            break

                        else:
                            # This is the case when BLAST was successful
                            xblast_result = xblast_result_handle.read()
                        
                        xf = open(xf_address, 'wb')
                        xf.write(xblast_result)
                        xf.close()
                        print 'Local BLASTx profile for %s complete' \
                            % coreg_gene.TTHERM_ID
                        logging.info('Local BLASTx profile for %s complete' \
                            % coreg_gene.TTHERM_ID)

                        drop_xf = open(drop_xf_address, 'wb')
                        drop_xf.write(xblast_result)
                        drop_xf.close()
                        print 'Dropbox BLASTx profile for %s complete' \
                            % coreg_gene.TTHERM_ID
                        logging.info('Dropbox BLASTx profile for %s complete' \
                            % coreg_gene.TTHERM_ID)

                    # Case when Dropbox file exists, but local does not:
                    # Copy Dropbox file to local directory!
                    # I am prioritizing keeping the Dropbox and local files
                    # equivalent over necessarily having the most current file
                    elif not os.path.exists(xf_address) and \
                        os.path.exists(drop_xf_address):

                        src = drop_xf_address
                        dst = xf_address

                        shutil.copy2(src, dst)
                        print 'Copied Dropbox BLASTx profile for %s to the ' \
                            'local folder.' % coreg_gene.TTHERM_ID
                        logging.info('Copied Dropbox BLASTx profile for %s to the ' \
                            'local folder.' % coreg_gene.TTHERM_ID)

                    # Case when local file exists, but the Dropbox one does not
                    # Reverse of case immediately above
                    elif os.path.exists(xf_address) and \
                        not os.path.exists(drop_xf_address):

                        src = xf_address
                        dst = drop_xf_address

                        shutil.copy2(src, dst)
                        print 'Copied local BLASTx profile for %s to the ' \
                            'Dropbox folder.' % coreg_gene.TTHERM_ID
                        logging.info('Copied local BLASTx profile for %s to the ' \
                            'Dropbox folder.' % coreg_gene.TTHERM_ID)

                    # Case when both local and Dropbox files exist:
                    # leave everything as is!
                    elif os.path.exists(xf_address) and \
                        os.path.exists(drop_xf_address):

                        print 'Both the local and Dropbox BLASTx profiles ' \
                            'for %s already exist' % coreg_gene.TTHERM_ID
                        logging.info('Both the local and Dropbox BLASTx profiles ' \
                            'for %s already exist' % coreg_gene.TTHERM_ID)

                # Here the user only wants local files, so we can keep the 
                # same approach as before Dropbox integration
                elif syncOption == 3:
                    if not os.path.exists(xf_address):
                        xblast_result_handle = NCBIWWW.qblast("blastx", "nr", 
                            coreg_gene.cDNA[10:],
                            genetic_code = 'Ciliate Nuclear',
                            entrez_query = entrez)
                        BLASTs_performed += 1

                        if not xblast_result_handle:
                            print 'BLASTx for %s failed. Skipping...' \
                                % coreg_gene.TTHERM_ID
                            logging.info('BLASTx for %s failed. Skipping...' \
                                % coreg_gene.TTHERM_ID)
                            break

                        else:
                            # This is the case when BLAST was successful
                            xblast_result = xblast_result_handle.read()

                        xf = open(xf_address, 'wb')
                        xf.write(xblast_result)
                        xf.close()
                        print 'Local BLASTx profile for %s complete' \
                            % coreg_gene.TTHERM_ID
                        logging.info('Local BLASTx profile for %s complete' \
                            % coreg_gene.TTHERM_ID)

                    else:
                        print 'The local BLASTx profile for %s already exists'\
                            % coreg_gene.TTHERM_ID

                # Then run BLASTp...
                # Case when user wants both Dropbox and local files
                # I do this for both syncOption == 1 or syncOption == 2 because
                # this should add speed if someone already ran the search to
                # Dropbox, which is one of my ultimate goals
                if syncOption != 3:
                    # Case when neither Dropbox nor local file exists:
                    # Write both!
                    if not os.path.exists(pf_address) and \
                        not os.path.exists(drop_pf_address):

                        pblast_result_handle = NCBIWWW.qblast("blastp", "nr", 
                            coreg_gene.protein[13:],
                            entrez_query = entrez)
                        BLASTs_performed += 1

                        if not pblast_result_handle:
                            print 'BLASTp for %s failed. Skipping...' \
                                % coreg_gene.TTHERM_ID
                            logging.info('BLASTp for %s failed. Skipping...' \
                                % coreg_gene.TTHERM_ID)
                            break

                        else:
                            # This is the case when BLAST was successful
                            pblast_result = pblast_result_handle.read()
                        
                        pf = open(pf_address, 'wb')
                        pf.write(pblast_result)
                        pf.close()
                        print 'Local BLASTp profile for %s complete' \
                            % coreg_gene.TTHERM_ID
                        logging.info('Local BLASTp profile for %s complete' \
                            % coreg_gene.TTHERM_ID)

                        drop_pf = open(drop_pf_address, 'wb')
                        drop_pf.write(pblast_result)
                        drop_pf.close()
                        print 'Dropbox BLASTp profile for %s complete' \
                            % coreg_gene.TTHERM_ID
                        logging.info('Dropbox BLASTp profile for %s complete' \
                            % coreg_gene.TTHERM_ID)

                    # Case when Dropbox file exists, but local does not:
                    # Copy Dropbox file to local directory!
                    # I am prioritizing keeping the Dropbox and local files
                    # equivalent over necessarily having the most current file
                    elif not os.path.exists(pf_address) and \
                        os.path.exists(drop_pf_address):

                        src = drop_pf_address
                        dst = pf_address

                        shutil.copy2(src, dst)
                        print 'Copied Dropbox BLASTp profile for %s to the ' \
                            'local folder.' % coreg_gene.TTHERM_ID
                        logging.info('Copied Dropbox BLASTp profile for %s to the ' \
                            'local folder.' % coreg_gene.TTHERM_ID)

                    # Case when local file exists, but the Dropbox one does not
                    # Reverse of case immediately above
                    elif os.path.exists(pf_address) and \
                        not os.path.exists(drop_pf_address):

                        src = pf_address
                        dst = drop_pf_address

                        shutil.copy2(src, dst)
                        print 'Copied local BLASTp profile for %s to the ' \
                            'Dropbox folder.' % coreg_gene.TTHERM_ID
                        logging.info('Copied local BLASTp profile for %s to the ' \
                            'Dropbox folder.' % coreg_gene.TTHERM_ID)

                    # Case when both local and Dropbox files exist:
                    # leave everything as is!
                    elif os.path.exists(pf_address) and \
                        os.path.exists(drop_pf_address):

                        print 'Both the local and Dropbox BLASTp profiles ' \
                            'for %s already exist' % coreg_gene.TTHERM_ID
                        logging.info('Both the local and Dropbox BLASTp profiles ' \
                            'for %s already exist' % coreg_gene.TTHERM_ID)

                # Here, the user wants nothing to do with Dropbox, so we can
                # keep things as before Dropbox integration
                elif syncOption == 3:
                    if not os.path.exists(pf_address):
                        pblast_result_handle = NCBIWWW.qblast("blastp", "nr", 
                            coreg_gene.protein[13:],
                            entrez_query = entrez)
                        BLASTs_performed += 1

                        if not pblast_result_handle:
                            print 'BLASTp for %s failed. Skipping...' \
                                % coreg_gene.TTHERM_ID
                            logging.info('BLASTp for %s failed. Skipping...' \
                                % coreg_gene.TTHERM_ID)
                            break

                        else:
                            # This is the case when BLAST was successful
                            pblast_result = pblast_result_handle.read()
                        
                        pf = open(pf_address, 'wb')
                        pf.write(pblast_result)
                        pf.close()
                        print 'Local BLASTp profile for %s complete' \
                            % coreg_gene.TTHERM_ID
                        logging.info('Local BLASTp profile for %s complete' \
                            % coreg_gene.TTHERM_ID)

                    else:
                        print 'The local BLASTp profile for %s already exists'\
                            % coreg_gene.TTHERM_ID
                        logging.info('The local BLASTp profile for %s already exists'\
                            % coreg_gene.TTHERM_ID)
         
    return



# Open BLAST result for every gene in the coregulated set in turn (i.e. looks
# through the pickled coreg_list file). Checks each hit def for 
# orthology by going to the TGD BLAST server.
# Look only at the top hit from each species (use regex) and discard others.
def reciprocal_BLAST(blast_address, coreg_gene,
    blastOption, clade):
    """ Use BLAST result reading from CoregFilesIO. 

        Called by get_BLAST_homologues_dict in CoregFilesIO

        parameters:
        blast_address, provided by get_BLAST_homologues_dict
        coreg_gene
        blastOption, for file name
        clade, for file name


    """
    # pdb.set_trace()
    print
    # blast_adress given as parameter
    tree = ET.parse(blast_address)

    root = tree.getroot()

    # First make sure that each species is represented in the BLAST 
    # results only once. Use the same regex as used in CoregFilesIO
    # to clean up the results for phrase analysis. I noticed that 
    # There is one species listing in the form '[[genus] species]'
    # that was causing me trouble, so I modified the regex. It seems
    # to work.

    speciesRegex = r'\[{1,2}[^\[]*\]'

    hitDefs = [hitDef.text for hitDef in root.iter('Hit_def')]

    specList = []
    hitRemovalList = []

    for hitDef in hitDefs:
        specObj = re.search(speciesRegex, hitDef)
        if specObj:
            if specObj.group() not in specList:
                specList.append(specObj.group())

    for spec in specList:
        specCount = 0
        for hitDef in hitDefs:
            if spec in hitDef:
                specCount += 1
                if specCount > 1:
                    hitRemovalList.append(hitDef)

    hitDelCount = 0
    for target in hitRemovalList:
        for hit in root.iter('Hit'):
            if target == hit.find('Hit_def').text:

                # For some reason, when removing nodes from XML files with
                # this library, the node has to be referenced relative to
                # its direct parent.
                parent = root.find('BlastOutput_iterations').find(
                    'Iteration').find('Iteration_hits')
                parent.remove(hit)

                hitDelCount += 1
                break

    print 'Removed %d redundant homologs' % hitDelCount
    logging.info('Removed %d redundant homologs' % hitDelCount)
    


    ########## OPTION 1: Use the TGD Server and selenium ###########
    # idList will get all of the gi IDs for the homologs. These gi IDs will be
    # used to find full protein sequences for eah homolog with Bio.Entrez. 
    # These sequences will, in turn, be used for the reciprocal BLASTs.
    # GIidList will only have the gi codes without extraneous information
    # GIidDict will have the gi code as key and protein sequence as item

    #August 5, 2016
    #updating to migrate from gi ids to accession.version.
    accessionseqDict = {}

    # Much better way than the commented-out chunk below.
    accessionidList = [ids.text for ids in root.iter('Hit_accession')]

    for accession in accessionidList:
        # Figured this out from Biopython tutorial section 9
        handle = Entrez.efetch(db='protein', id=accession, retmode='xml')
        record = Entrez.read(handle)
        handle.close()
        accessionseqDict[accession] = record[0]['GBSeq_sequence']

    # Initialize an empty list that will contain all accession ids to remove
    # because I am confident that they are not informative
    removalList = []

    # Initialize an empty list that will contain all accession ids that are more
    # likely paralogs than orthologs, but may still be informative
    paralogList = []

    # Initialize an empty list that will contain all accession ids that are 
    # predicted to be informative orthologs
    orthologList = []

    quality_dict = {}

    # loop over the keys (accession.versions) for the given gene from the coreg_list, as
    # named by coreg_gene.TTHERM_ID
    for accessionKey in accessionseqDict:
        print
        print
        print 'Reciprocating next homolog with accession.version %s and sequence' % accessionKey
        logging.info('Reciprocating next homolog with accession.version %s and sequence' % accessionKey)
        print accessionseqDict[accessionKey]
        logging.info(accessionseqDict[accessionKey])
        print
        recipDone = False
        recipAttemptNum = 1
        while not recipDone:
            try:
                # Go to the TGD BLAST server
                result = requests.post('http://www.ciliate.org/blast/blast_link_result.cgi',
                    data = {"FILTER": 'L', "PROGRAM": 'blastp', "DATALIB": 'tetrahymena/ttherm.aa', 
                    "SEQUENCE": accessionseqDict[accessionKey]})

                result_soup = bs4.BeautifulSoup(result.text, 'html5lib')

                # if browser.title == u'':
                #     # Database selection messed up
                #     recipAttemptNum += 1
                #     continue

                # elif browser.title == u'BLAST Search Results':
                    # Everything seems to have worked, but check if there are hits
                check = result_soup.find_all('pre')[1].text
                if '***** No hits found ******' in check:
                    # Nothing was found
                    print 'There were no hits for the homolog with accession.version: %s' % accessionKey
                    logging.info('There were no hits for the homolog with accession.version: %s' % accessionKey)
                    removalList.append(accessionKey)
                    quality_dict[accessionKey] = 'remove'
                    topRecipHit = 'fail'
                    recipDone = True
                    break

            except:
                print 'There was an error:'
                raise
                topRecipHit = 'fail'
                recipDone = True
                break

            else:
                # Everything worked 
                # Get the top hit
                # Dumps all of the results in one big string  
                reciprocalResults = result_soup.find_all('pre')[2]
                topRecipHit = str(reciprocalResults.find_all('a')[0].text)


                if reciprocalResults == '':
                    print 'There were no results for this sequence'
                    logging.info('There were no results for this sequence')
                    reciprocalResults = None
                    recipDone = True

                else:
                    # Got the reciprocalHit:
                    reciprocalList = reciprocalResults.text.split('\n')
                    for i in range(5):
                        reciprocalList.pop(0)

                    reciprocalList.pop(-1)

                    recipDict = {}

                    for hit in reciprocalList:
                        items = re.split('\s\s+', hit)
                        recipDict[items[0]] = [items[1], items[3]]

                    recipDone = True
                    break


        if topRecipHit == 'fail':
            # Go to the next sequence without doing anything
            # time.sleep(1)
            continue
        
        elif coreg_gene.TTHERM_ID == topRecipHit:
            print 'Putative ortholog found.'
            logging.info('Putative ortholog found.')
            quality_dict[accessionKey] = 'ortholog'
            orthologList.append(accessionKey)
            print
            print

        elif coreg_gene.TTHERM_ID not in recipDict.keys():
            print 'Reciprocal BLAST not even close.'
            logging.info('Reciprocal BLAST not even close.')
            quality_dict[accessionKey] = 'remove'
            removalList.append(accessionKey)
            pass
            print
            print


        # 2017_01_23: Change to a more systematic analysis. Take
        # reciprocal BLASTs as correct if e-value of original Tetrahymena
        # gene is within two orders of magnitude of the top hit

        elif (topRecipHit != coreg_gene.TTHERM_ID):
                
            if coreg_gene.TTHERM_ID in recipDict.keys():                
                topRecipHit_eval = str(recipDict[topRecipHit][1]).strip()
                if topRecipHit_eval[0] == 'e':
                    topRecipHit_eval = '1' + topRecipHit_eval
                topRecipHit_eval = float(topRecipHit_eval)

                target_eval = str(recipDict[coreg_gene.TTHERM_ID][1]).strip()
                if target_eval[0] == 'e':
                    target_eval = '1' + target_eval
                target_eval = float(target_eval)

                try:

                    if topRecipHit_eval / target_eval >= 0.01:
                        print "e-value within two orders of magnitude of top hit: accepting as putative ortholog."
                        logging.info("e-value within two orders of magnitude of top hit: accepting as putative ortholog.")
                        orthologList.append(accessionKey)
                        quality_dict[accessionKey] = 'ortholog'
                        print
                        print

                    elif (topRecipHit_eval / target_eval < 0.01) and \
                    (recipDict[topRecipHit][0] == recipDict[coreg_gene.TTHERM_ID][0]):
                        print "This gene is likely a paralog, but may still be informative."
                        logging.info("This gene is likely a paralog, but may still be informative.")
                        paralogList.append(accessionKey)
                        quality_dict[accessionKey] = 'paralog'
                        print
                        print
                    
                    else:
                        print "This gene is likely an uninformative paralog."
                        logging.info('This gene is likely an uninformative paralog.')
                        removalList.append(accessionKey)
                        quality_dict[accessionKey] = 'remove'
                        print
                        print
                except:
                    # Target e_value equals zero. I think we should take this
                    # even in the cases when it isn't the top hit for some
                    # reason
                    print 'Putative ortholog found.'
                    logging.info('Putative ortholog found.')
                    quality_dict[accessionKey] = 'ortholog'
                    orthologList.append(accessionKey)
                    print
                    print                    

    # Remove the uninformative homolog. Iterate over the hits_ids in the
    # forward BLAST data
    # file, then iterate over the GI codes in removalList. If the code
    # in the removal list matches the code in the hit, remove that hit
    # from the data file.

    # Iterate over all the hits, then add an attributed to the Hit_def
    # tag to show whether the hit is an ortholog or paralog, or if it
    # should be removed from further analysis.

    for hit in root.iter('Hit'):
        key = hit.find('Hit_accession').text
        plan = quality_dict[key]
        hit_def = hit.find('Hit_def')
        if plan == 'ortholog':
            hit_def.set('quality', 'ortholog')
        elif plan == 'paralog':
            hit_def.set('quality', 'paralog')
        elif plan == 'remove':
            hit_def.set('quality', 'remove')                                

    print 'Marked the following homologs for removal from analysis: '
    logging.info('Marked the following homologs for removal from analysis: ' )
    print removalList

    # return new XML data without the paralogs. The file will be written by
    # the higher level function CoregFilesIO.get_BLAST_homologues_dict()
    return (tree, orthologList, paralogList)

