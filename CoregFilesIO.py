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


import os
import sys
import platform
import time
import re
import dill
import difflib
import csv
import pdb
import shutil
import CoregulationDataHarvester
import BLASTmod
import time
import logging
import filename_generator
import xml.etree.ElementTree as ET

if platform.system() == 'Windows':
    from win32com.shell import shell, shellcon

def get_best_reciprocal_longest_matches(phrase_dict):
    """ Get two phrases from the ones found by 
        longest_phrases_in_homologue_info. Put the one with the most counts
        and the one that is longest (the two 'best' phrases) into the
        dictionary bestDict.

        To really understand how this function works, please read through 
        the below functions, so that you understand the basis of the data 
        structures.
    """

    bestPhraseDict = {}
    for key1 in phrase_dict:
        bestPhraseDict[key1] = [0, 0]
        best = 0
        longest = 0
        
        for key2 in phrase_dict[key1]:
            #Find match that had the most counts
            if phrase_dict[key1][key2] > best:
                
                bestPhraseDict[key1].pop(0)
                bestPhraseDict[key1].insert(0, key2)
                best = phrase_dict[key1][key2]
        
        for key2 in phrase_dict[key1]:
            # Find longest match
            if len(key2) > longest:
                bestPhraseDict[key1].pop(1)
                bestPhraseDict[key1].insert(1, key2)
                longest = len(key2)


    return bestPhraseDict


def clean_homologue_info(raw_homologue_dict, clade):
    """ There are two purposes to this function: to remove pesky >gi 
        identifiers that pop up in some of the homology hit info, and
        to note explicitly when there is no homology information outside of
        the ciliates (recall that the qBLAST is set to exclude all ciliate
        matches)

        input: raw_homologue_dict
            keys are TTHERM_IDs; value is a list of lists, where each little 
            list is a given homolog's definition and its quality
        output: cleaned up raw_homologue_dict

        This function is called into get_BLAST_homologues_dict as the cleanup
        step.
    """

    for key in raw_homologue_dict:
        # First, check if there were any hits. If not, say so explicitly
        # in the else statement
        if raw_homologue_dict[key] != []:

            # This is the business part of the function:
            # I really want to remove all of the >gi identifiers that for some
            # reason pollute some gene info. They have multiple forms.
            # some examples:
            # >gi|662197993|ref|XP_008472102.1|
            # >gi|9743353|gb|AAF97977.1|AC000103_27
            # >gi|13878785|sp|Q9UY36.1|SYA_PYRAB
            # >gi|306440712|pdb|3OFI|A
            # The main observation, though, is simple: each starts with
            # >gi and has no spaces! The regex is pretty simple. It matches
            # anything that starts with >gi, and doesn't contain spaces. 
            # If you want to mess around with
            # the regex, uncomment the print statement. That will let you see
            # what exactly is getting booted out by the function.

            # Each loop tracks the list for each key, as well as its index
            # I'm actually not %100 sure how this works. I feel like the index
            # should always end up being 0 because each key has only one list
            # assigned, but I'm not sure. I will figure this out.
            for index, info in enumerate(raw_homologue_dict[key]):
                # info is the list [definition, quality]

                # regex for getting all the gi codes
                regex1 = r'(\>gi[^\s]*)'
                # regex for getting all the [genus species]. I noticed that 
                # There is one species listing in the form '[[genus] species]'
                # that was causing me trouble, so I modified the regex. It seems
                # to work.
                regex2 = r'\[{1,2}[^\[]*\]'

                # remove gi codes, [genus species], and extra left-over 
                # whitespace
                info_nogi = re.sub(regex1, '', info[0])
                info_noSpecies = re.sub(regex2, '', info_nogi)
                cleaned_info = re.sub(r'\s{2,}', ' ', info_noSpecies)
                # pdb.set_trace()
                raw_homologue_dict[key][index][0] = cleaned_info
        else:
            # Empty lists get explicitly explained (see above)
            raw_homologue_dict[key].append(
                    ['No informative homologs found', 'empty'])
    # pdb.set_trace()

    clean_homologue_dict = raw_homologue_dict

    return clean_homologue_dict

def get_BLAST_homologues_dict(
    formatted_TTHERM_ID_list, threshold, owOption, syncOption, blastOption, clade):
    """ Read through XML file and take all the hit info for the gene.
        Probably build a single dictionary that encompasses all genes in
        the coregulated group:
            - Gene is key
            - Homology info is item (a list of list of hit definitions and 
            their quality)

        input: formatted_TTHERM_ID_list, z-score threshold, owOption for file-handling,
        syncOption for Dropbox handling, andblastOption and clade for
        finding the correct file names, 

        process: unpickle coregs_zscores_cDNA_list in order to find the list of
        genes to work with. Parse BLAST results for those genes and build a 
        dictionary. Call BLASTmod.reciprocal_BLAST to get process the raw
        BLAST results so that they no longer have redundant homologs or
        paralogs. Call clean_homologue_info() to clean the dictionary up from
        various NCBI gi codes, species identification, etc..

        output: a dictionary where each key is the TTHERM_ID of a gene in the
        coregulated gene group, and each value is a list of lists. The little
        lists in the the item are a cleaned up homolog definition and its
        quality (ortholog, paralog, or remove). I am calling this 
        clean_homologue_dict.

        NOTE: always called with either BLASTp or BLASTx as the BLAST option.
        If the user specified that they want both, then the function is run
        twice, once with each. Otherwise, there is no good way to identify
        file names!
    """
    # Unpickle the file with coregs_zscores_cDNA_list for the given TTHERM_ID
    # and threshold for the search.


    pickled_coregs_cDNA_address, drop_pickled_coregs_cDNA_file = filename_generator.filename_generator('coregs_zscores',
    	formatted_TTHERM_ID_list)
    p_homodict_pickle_address, x_homodict_pickle_address = filename_generator.filename_generator(
    	'homologue_dict', formatted_TTHERM_ID_list, threshold = threshold)

    pickled_coregs_cDNA_file = open(pickled_coregs_cDNA_address, 'rb')
    coregs_zscores_cDNA_list = dill.load(pickled_coregs_cDNA_file)

    toBLAST = BLASTmod.to_blast(coregs_zscores_cDNA_list, formatted_TTHERM_ID_list, threshold)

    # Initialize the dictionary where everything will go
    raw_homologue_dict = {}
    for coreg_gene in toBLAST:
        list_TTHERM_ID = []
        list_TTHERM_ID.append(coreg_gene.TTHERM_ID)
    	blast_address, drop_blast_address, reciprocal_blast_address, drop_reciprocal_blast_address = \
            filename_generator.filename_generator('blast', list_TTHERM_ID, 
    			clade = clade, blastOption = blastOption)
        # pdb.set_trace()

        # blast_address is the address of the 'raw' BLAST results
        # reciprocal_blast_adress is the address of the BLAST results that have 
        # been processed to remove all but the top hit for each species and
        # marked according to quality.
        print

        # Figure out syncing with Dropbox. Again, if the BLAST file(s) exist
        # in Dropbox AND the user selected to make any sort of use of Dropbox
        # AND the user selected to reuse previously made files, then overwrite
        # the local files (extant or not) with the Dropbox files. This will 
        # help keep file versions consistent over the cloud.

        # Also, figure out overwriting options. If the user does not want 
        # already existing BLAST results to be overwritten, then existing
        # reciprocal BLAST results shouldn't be overwritten either.
        if owOption != 3:
            # Overwrite BLASTs, include Dropbox files if syncOption != 3.
            print 'Initiating reciprocal %s analysis for %s' \
                % (blastOption, coreg_gene.TTHERM_ID)
            logging.info('Initiating reciprocal %s analysis for %s' \
                % (blastOption, coreg_gene.TTHERM_ID))
            
            recipTree = BLASTmod.reciprocal_BLAST(
                blast_address, coreg_gene, blastOption, clade)[0]


            if syncOption == 1:
                # Write both locally and to Dropbox
                print 'Writing reciprocal BLAST results both locally and to Dropbox'
                logging.info('Writing reciprocal BLAST results both locally and to Dropbox')
                recipTree.write(drop_reciprocal_blast_address)
                recipTree.write(reciprocal_blast_address)

            elif syncOption == 2:
                # Write only to Dropbox
                print 'Writing reciprocal BLAST results to Dropbox'
                logging.info('Writing reciprocal BLAST results to Dropbox')
                recipTree.write(drop_reciprocal_blast_address)

            elif syncOption == 3:
                # Write only locally
                print 'Writing reciprocal BLAST results locally'
                logging.info('Writing reciprocal BLAST results locally')
                recipTree.write(reciprocal_blast_address)

        elif owOption == 3:
            # Keep everything possible
            if syncOption != 3:
                if os.path.exists(drop_reciprocal_blast_address):
                    # Use the Dropbox version of the file, copy it locally
                    print 'Found Dropbox copy of reciprocally filtered %s for %s' \
                        % (blastOption, coreg_gene.TTHERM_ID)
                    print 'Copying these results locally for synchronization.'

                    logging.info('Found Dropbox copy of reciprocally filtered %s for %s' \
                        % (blastOption, coreg_gene.TTHERM_ID)) 
                    logging.info('Copying these results locally for synchronization.')

                    src = drop_reciprocal_blast_address
                    dst = reciprocal_blast_address
                    shutil.copy2(src, dst)

                elif not os.path.exists(drop_reciprocal_blast_address) and\
                    os.path.exists(reciprocal_blast_address):
                    # Use the local version and copy it to dropbox
                    print 'Found local copy of reciprocally filtered %s for %s' \
                        % (blastOption, coreg_gene.TTHERM_ID)
                    print 'that is absent in Dropbox. Copying to Dropbox for synchronization.'
                    logging.info('Found local copy of reciprocally filtered %s for %s that is absent in Dropbox. Copying to Dropbox for synchronization.'.format(blastOption, coreg_gene.TTHERM_ID))
                    src = reciprocal_blast_address
                    dst = drop_reciprocal_blast_address
                    shutil.copy2(src, dst)

                elif not os.path.exists(drop_reciprocal_blast_address) and\
                    not os.path.exists(reciprocal_blast_address):

                    # Call the reciprocal analysis from BLASTmod
                    print 'No reciprocal %s for %s found.' \
                        % (blastOption, coreg_gene.TTHERM_ID)
                    logging.info('No reciprocal %s for %s found.' \
                        % (blastOption, coreg_gene.TTHERM_ID))

                    print 'Beginning reciprocal %s analysis for %s'\
                        % (blastOption, coreg_gene.TTHERM_ID)
                    logging.info('Beginning reciprocal %s analysis for %s'\
                        % (blastOption, coreg_gene.TTHERM_ID))
                    # pdb.set_trace()
                    recipTree = BLASTmod.reciprocal_BLAST(
                        blast_address, coreg_gene, 
                        blastOption, clade)[0]

                    if syncOption == 1:
                        # User wants both local and Dropbox
                        recipTree.write(drop_reciprocal_blast_address)
                        recipTree.write(reciprocal_blast_address)

                    elif syncOption == 2:
                        # User only wants to write to Dropbox
                        recipTree.write(drop_reciprocal_blast_address)

                    elif syncOption == 3:
                        # User only wants to write locally
                        recipTree.write(reciprocal_blast_address)

            elif syncOption == 3:
                # User only want to run things locally
                if os.path.exists(reciprocal_blast_address):
                    print 'Found local copy of reciprocally filtered %s for %s.'\
                        % (blastOption, coreg_gene.TTHERM_ID)
                    print 'This version will be used for analysis.'
                    logging.info('Found local copy of reciprocally filtered %s for %s. This version will be used for analysis.'\
                        % (blastOption, coreg_gene.TTHERM_ID))
                    pass

                elif not os.path.exists(reciprocal_blast_address):
                    print 'No local copy of reciprocally filtered %s found'\
                        % blastOption
                    logging.info('No local copy of reciprocally filtered %s found'\
                        % blastOption)
                    print 'Beginning reciprocal %s analysis for %s' \
                        % (blastOption, coreg_gene.TTHERM_ID)
                    logging.info('Beginning reciprocal %s analysis for %s' \
                        % (blastOption, coreg_gene.TTHERM_ID))
                    recipTree = BLASTmod.reciprocal_BLAST(
                        blast_address, coreg_gene, 
                        blastOption, clade)[0]

                    recipTree.write(reciprocal_blast_address)


        # When the file doesn't exist, it cannot be parsed and throws an error
        try:
            tree = ET.parse(reciprocal_blast_address)
        except:
            print 'No file for %s found. Skipping...' % coreg_gene.TTHERM_ID
            logging.info('No file for %s found. Skipping...' % coreg_gene.TTHERM_ID)
            continue

        root = tree.getroot()

        # Populate the dictionary. Assigns a list of lists of all homology 
        # hits and their respective qualities to a gene. Sometimes, there 
        # are no homology hits due to a database error
        # I make an explicit note of that.

        # Use a list comprehension here to make an item for the
        # raw_homologue_dict, with the key being the current gene ID
        # and value being a list of the definition and its quality
        raw_homologue_dict[coreg_gene.TTHERM_ID] = [
        [hit_d.text, hit_d.get('quality')] for hit_d in root.iter(
            'Hit_def')]

        # Check for database error from BLAST
        if raw_homologue_dict[coreg_gene.TTHERM_ID] == []:
            for message in root.iter('Iteration_message'):
                if message.text == '[blastsrv4.REAL]: '\
                    'Error: CPU usage limit was exceeded, '\
                        'resulting in SIGXCPU (24).' \
                        or 'Failed to collect db stats for nr' in message.text:
                    raw_homologue_dict[coreg_gene.TTHERM_ID] = [[
                    'db error', 'error']]

        print 'End reciprocal BLASTs'
        logging.info('End reciprocal BLASTs')
        
        # END LOOP
    pickled_coregs_cDNA_file.close()

    # Cleanup
    clean_homologue_dict = clean_homologue_info(raw_homologue_dict, clade)
    # pdb.set_trace()


    # Pickle the homologue info dictionary for later use
    if blastOption == 'blastx':
        pickle_f = open(x_homodict_pickle_address, 'wb')
        dill.dump(clean_homologue_dict, pickle_f)
        pickle_f.close()

    elif blastOption == 'blastp':
        pickle_f = open(p_homodict_pickle_address, 'wb')
        dill.dump(clean_homologue_dict, pickle_f)
        pickle_f.close()

    # pdb.set_trace()             

    return clean_homologue_dict

def separate_orthologs_and_paralogs(clean_homologue_dict):
    """
    return dictionaries that are either all ortholog definitions, all
    paralog definitions, or a mix of paralogs and orthologs
    """
    # pdb.set_trace()
    ortho_dict = {}
    para_dict = {}
    mix_dict = {}

    for key in clean_homologue_dict:
        ortho_dict[key] = []
        para_dict[key] = []
        mix_dict[key] = []
        for l in clean_homologue_dict[key]:
            if l[1] == 'ortholog':
                ortho_dict[key].append(l[0])
                mix_dict[key].append(l[0])
            elif l[1] == 'paralog':
                para_dict[key].append(l[0])
                mix_dict[key].append(l[0])
            elif l[1] == 'empty':
                ortho_dict[key].append('No informative homologs found')
                para_dict[key].append('No informative homologs found')
                mix_dict[key].append('No informative homologs found')
            elif l[1] == 'error':
                ortho_dict[key].append('db error')
                para_dict[key].append('db error')
                mix_dict[key].append('db error')                
    # pdb.set_trace()
    return ortho_dict, para_dict, mix_dict


def longest_phrases_in_homologue_info(homologue_dict):
    """ Initialize an empty dictionary of dictionaries:
        The inner dictionary will contain the phrases found as
        keys, and the amount of times they have been found as items.
        The outer dictionary will contain the gene names as keys and phrase 
        dictionaries as items.

        input the dictionary with gene names as keys and the list of homologue
        information as the item for each key. This should be the cleaned up
        version of the homologue_dict made above. In a for-loop, go through
        each key (gene name) in the dictionary.
    """
    # Initialize dictionary
    dict_of_genes_of_phrases = {}
    # pdb.set_trace()

    for key in homologue_dict:
        # Initialize internal dictionary
        dict_of_genes_of_phrases[key] = {}

        # Some genes have only two homologues, and the pairwise comparison may
        # be not informative...
        if len(homologue_dict[key]) > 2:
            # Keep the first phrase to compare constant, while all the others 
            # change. This next loop is simply for the index of the first
            # string in the list. 
            for i in xrange(len(homologue_dict[key])):

                # Get the index for each string in the list of strings that is
                # stored under the key in the dictionary homologue_dict.
                for index in xrange(len(homologue_dict[key])):

                    # Check that my for loop doesn't go beyond the length of
                    # the list strings stored uder the key. Since I am 
                    # comparing the strings pairwise, I need to stop at 
                    # comparing with the last string. I am adding the two
                    # indices from the two for inner for loops so that it 
                    # always begins by comparing a string to the one 
                    # immediately following it. I.e. if I am starting with
                    # string #1, it will be compared to string #2, then #3,
                    # and so on, until the list is exhausted. At that point we
                    # go into the loop above this one, start with string #2,
                    # compare it with string #3, and so on, and so on...
                    if index + i + 1 < len(homologue_dict[key]): 

                        # Remove any punctuation/ capitalization that may
                        # intefere with finding common phrases between each 
                        # pair. My re.sub replaces everything that isn't 
                        # alphanumeric, a space, a dash, a forward slash,
                        # an equals sign, or parantheses with an empty ''. 
                        regex = r'[^A-Za-z0-9\s\-\/\=\(\)]+'
                        s1 = re.sub(regex, '', homologue_dict[key][i].lower())
                        s2 = re.sub(regex, 
                            '', homologue_dict[key][index + i + 1].lower())

                        # Get the handler for the SequenceMatcher.
                        mh = difflib.SequenceMatcher(None, s1, s2)
                        
                        # difflib.SequenceMatcher.find_longest_match() takes
                        # the beginning and end positions in the two strings, 
                        # and returns a tuple (i, j, k) where 
                        # s1[i: i + k] = s2[j: j + k],
                        # which is the longest phrase matched. See the python
                        # standard library docs for more.
                        m = mh.find_longest_match(0, len(s1), 0, len(s2))

                        # Strip off any whitespace from the matched phrase. I
                        # made an obtuse if-statement to remove at least some
                        # uninformative results. If the phrase passes that
                        # test, then it is added as a key to the inner
                        # dictionary and the counter is updated if that key
                        # already exists.
                        phrase = (s1[m[0]:(m[0] + m[2])]).strip(' -=/')
                        
                        # If most of the phrase consists of 'hypothetical 
                        # protein', ignore that phrase
                        if 'hypothetical protein' in phrase:
                            if len('hypothetical protein')/\
                                float(len(phrase)) > 0.6:  
                                pass

                        # A crude filter, but seems to work
                        elif (phrase != '')\
                            and (phrase != 'unknown')\
                            and (phrase != 'repeat-containing protein')\
                            and (phrase != 'domain-containing protein')\
                            and (phrase != 'peptid')\
                            and (phrase != 'terminal domain')\
                            and (phrase != 'containing protein')\
                            and (phrase != 'membrane')\
                            and (phrase != 'repeat')\
                            and (phrase not in 'conserved unknown protein')\
                            and (phrase not in 'protein '*3) \
                            and (phrase not in 'hypothetical protein '*3) \
                            and (phrase not in 'predicted protein '*3) \
                            and (phrase not in 'predicted '*3) \
                            and (phrase not in 'hypothetical '*3)\
                            and (phrase not\
                                in 'conserved hypothetical protein '*3) \
                            and (phrase not\
                                in 'hypothetical protein variant '*3) \
                            and (len(phrase) > 4):

                            dict_of_genes_of_phrases[key][phrase] = \
                                dict_of_genes_of_phrases[key].get(phrase,0) + 1


                        # If no inter-string matches, choose the longest string
                        # as the phrase
                        elif phrase == '':
                            longest = 0
                            longList = ['']
                            for string in homologue_dict[key]:
                                # Find longest match
                                if len(string) > longest:
                                    longList.pop(0)
                                    longList.insert(0, string)
                                    longest = len(string)
                            phrase = longList[0].lower().strip(' -=/')
                            dict_of_genes_of_phrases[key][phrase] = \
                                dict_of_genes_of_phrases[key].get(phrase,0) + 1

        
        # In the case when there are only two hits, just take both      
        elif len(homologue_dict[key]) == 2:
            regex = r'[^A-Za-z0-9\s\-\/\=\(\)]+'
            s1 = re.sub(regex, '', homologue_dict[key][0][0].lower()) 
            s2 = re.sub(regex, '', homologue_dict[key][1][0].lower())
            
            phrase1 = s1.strip(' -=/')
            dict_of_genes_of_phrases[key][phrase1] \
                = dict_of_genes_of_phrases[key].get(phrase1, 0) + 1 

            phrase2 = s2.strip(' -=/')
            dict_of_genes_of_phrases[key][phrase2] \
                = dict_of_genes_of_phrases[key].get(phrase2, 0) + 1


        # Case when there is one homologue
        elif len(homologue_dict[key]) == 1:
            regex = r'[^A-Za-z0-9\s\-\/\=\(\)]+'
            phrase = re.sub(regex, '', homologue_dict[key][0].lower())
            dict_of_genes_of_phrases[key][phrase] \
                    = dict_of_genes_of_phrases[key].get(phrase, 0) + 1

    # Try to reduce false negatives by checking again the
    # dict_of_genes_of_phrases for empty items. If an item is empty, scan 
    # through the homologue dict again, and see if there are any phrases
    # without 'hypothetical protein' in them.
    for key in dict_of_genes_of_phrases:
        if dict_of_genes_of_phrases[key] == {}:
            # pdb.set_trace()
            for string in homologue_dict[key]:
                if 'hypothetical protein' not in string and\
                    string not in 'predicted protein '*3 and\
                    string not in 'unnamed protein product '*3 and\
                    string not in 'uncharacterized protein '*3:
                    phrase = string.lower().strip(' -=/')
                    dict_of_genes_of_phrases[key][phrase] = \
                        dict_of_genes_of_phrases[key].get(phrase, 0) + 1


    return dict_of_genes_of_phrases

def dictionary_work(formatted_TTHERM_ID_list, threshold, owOption, 
    syncOption, blastOption, clade):
    ''' Combine all the above functions.
    '''
    p_bestdict_pickle_address, x_bestdict_pickle_address = filename_generator.filename_generator(
    	'best_phrase_dict', formatted_TTHERM_ID_list, threshold = threshold)

    # pdb.set_trace()
    if blastOption == 'blastx':
        homologue_dict = get_BLAST_homologues_dict(
                            formatted_TTHERM_ID_list, threshold, 
                            owOption, syncOption, blastOption, clade)

        ortho_dict, para_dict, mix_dict = separate_orthologs_and_paralogs(
            homologue_dict)
        
        ortho_phrase_dict = longest_phrases_in_homologue_info(ortho_dict)
        para_phrase_dict = longest_phrases_in_homologue_info(para_dict)
        mix_phrase_dict = longest_phrases_in_homologue_info(mix_dict)

        ortho_best = get_best_reciprocal_longest_matches(ortho_phrase_dict)
        para_best = get_best_reciprocal_longest_matches(para_phrase_dict)
        mix_best = get_best_reciprocal_longest_matches(mix_phrase_dict)

        # Now a dictionary of dictionaries: keep in mind for the CSV writing
        bestPhraseDict = {
            'ortho': ortho_best, 'para': para_best, 'mix': mix_best}

        pickle_f = open(x_bestdict_pickle_address, 'wb')
        dill.dump(bestPhraseDict, pickle_f)
        pickle_f.close()

    elif blastOption == 'blastp':
        homologue_dict = get_BLAST_homologues_dict(
                            formatted_TTHERM_ID_list, threshold, owOption, 
                            syncOption, blastOption, clade)

        ortho_dict, para_dict, mix_dict = separate_orthologs_and_paralogs(
            homologue_dict)
        
        ortho_phrase_dict = longest_phrases_in_homologue_info(ortho_dict)
        para_phrase_dict = longest_phrases_in_homologue_info(para_dict)
        mix_phrase_dict = longest_phrases_in_homologue_info(mix_dict)

        ortho_best = get_best_reciprocal_longest_matches(ortho_phrase_dict)
        para_best = get_best_reciprocal_longest_matches(para_phrase_dict)
        mix_best = get_best_reciprocal_longest_matches(mix_phrase_dict)

        # Now a dictionary of dictionaries: keep in mind for the CSV writing
        bestPhraseDict = {
            'ortho': ortho_best, 'para': para_best, 'mix': mix_best}
        # pdb.set_trace()
        pickle_f = open(p_bestdict_pickle_address, 'wb')
        dill.dump(bestPhraseDict, pickle_f)
        pickle_f.close()

    elif blastOption == 'both':
        # First do it for the BLASTx
        x_homologue_dict = get_BLAST_homologues_dict(
            formatted_TTHERM_ID_list, threshold, owOption, syncOption, 'blastx', clade)

        x_ortho_dict, x_para_dict, x_mix_dict = separate_orthologs_and_paralogs(
            x_homologue_dict)
        
        x_ortho_phrase_dict = longest_phrases_in_homologue_info(x_ortho_dict)
        x_para_phrase_dict = longest_phrases_in_homologue_info(x_para_dict)
        x_mix_phrase_dict = longest_phrases_in_homologue_info(x_mix_dict)

        x_ortho_best = get_best_reciprocal_longest_matches(x_ortho_phrase_dict)
        x_para_best = get_best_reciprocal_longest_matches(x_para_phrase_dict)
        x_mix_best = get_best_reciprocal_longest_matches(x_mix_phrase_dict)

        # Now a dictionary of dictionaries: keep in mind for the CSV writing
        x_bestPhraseDict = {
            'ortho': x_ortho_best, 'para': x_para_best, 'mix': x_mix_best}

        x_pickle_f = open(x_bestdict_pickle_address, 'wb')
        dill.dump(x_bestPhraseDict, x_pickle_f)
        x_pickle_f.close()

        # Then do it for BLASTp
        # Now a dictionary of dictionaries: keep in mind for the CSV writing
        p_homologue_dict = get_BLAST_homologues_dict(
            formatted_TTHERM_ID_list, threshold, owOption, syncOption, 'blastp', clade)

        p_ortho_dict, p_para_dict, p_mix_dict = separate_orthologs_and_paralogs(
            p_homologue_dict)
        
        p_ortho_phrase_dict = longest_phrases_in_homologue_info(p_ortho_dict)
        p_para_phrase_dict = longest_phrases_in_homologue_info(p_para_dict)
        p_mix_phrase_dict = longest_phrases_in_homologue_info(p_mix_dict)

        p_ortho_best = get_best_reciprocal_longest_matches(p_ortho_phrase_dict)
        p_para_best = get_best_reciprocal_longest_matches(p_para_phrase_dict)
        p_mix_best = get_best_reciprocal_longest_matches(p_mix_phrase_dict)

        p_bestPhraseDict = {
            'ortho': p_ortho_best, 'para': p_para_best, 'mix': p_mix_best}

        p_pickle_f = open(p_bestdict_pickle_address, 'wb')
        dill.dump(p_bestPhraseDict, p_pickle_f)
        p_pickle_f.close()

    return

def append_summaries_to_csv_row(bestPhraseDict, row, key):

    try:
        # pdb.set_trace()
        ortho_summary = bestPhraseDict['ortho'][key][0]
        para_summary = bestPhraseDict['para'][key][0]
        mix_summary = bestPhraseDict['mix'][key][0]
        mix_long_summary = bestPhraseDict['mix'][key][1]
        
        if ortho_summary == 0:
            ortho_summary = 'Orthologs found, but summary is uninformative'
        elif ortho_summary == '':
            ortho_summary = 'No BLAST performed'
        elif len(ortho_summary) == 1:
            ortho_summary = 'Definitions too dissimilar to summarize'

        if para_summary == 0:
            para_summary = 'Paralogs found, but summary is uninformative'
        elif para_summary == '':
            para_summary = 'No BLAST performed'
        elif len(para_summary) == 1:
            para_summary = 'Definitions too dissimilar to summarize'
    
        if mix_summary == 0:
            mix_summary = 'Homologs found, but nothing informative'
        elif mix_summary == '':
            mix_summary = 'No BLAST performed'                 
        elif len(mix_summary) == 1:
            mix_summary = 'Definitions too dissimilar to summarize' 

        if mix_long_summary == 0:
            mix_long_summary = 'Homologs found, but summary is uninformative'
        elif mix_long_summary == '':
            mix_long_summary = 'No BLAST performed'
        elif len(mix_long_summary) == 1:
            mix_long_summary = 'Definitions too dissimilar to summarize' 

    except:
        ortho_summary = 'No reciprocal BLASTs performed'
        para_summary = 'No reciprocal BLASTs performed'
        mix_summary = 'No reciprocal BLASTs performed'
        mix_long_summary = 'No reciprocal BLASTs performed'

    row.append(ortho_summary)
    row.append(para_summary)
    row.append(mix_summary)
    row.append(mix_long_summary)

    return row

def make_CSV(formatted_TTHERM_ID_list, threshold, blastOption, clade):
    """ Take bestPhraseDict and coregs_zscores_cDNA_list (unpickle). Write .csv
        file that is in the excel dialect: 
            GeneID,CommonName,Description,z-score,BLAST_analyses

    """

    # Unpickle coregs_zscores_cDNA_list and bestPhraseDict
    pickled_coregs_cDNA_address, drop_pickled_coregs_cDNA_file  = filename_generator.filename_generator('coregs_zscores',
    	formatted_TTHERM_ID_list)
    p_bestdict_pickle_address, x_bestdict_pickle_address = filename_generator.filename_generator(
    	'best_phrase_dict', formatted_TTHERM_ID_list, threshold = threshold)

    # Load the files into manipulable objects
    pickled_coregs_cDNA_file = open(pickled_coregs_cDNA_address, 'rb')
    coregs_zscores_cDNA_list = dill.load(pickled_coregs_cDNA_file)
    pickled_coregs_cDNA_file.close()

    if blastOption == 'blastx':
        x_pickled_bestPhraseDict_file = open(x_bestdict_pickle_address, 'rb')
        x_bestPhraseDict = dill.load(x_pickled_bestPhraseDict_file)
        x_pickled_bestPhraseDict_file.close()

    elif blastOption == 'blastp':
        p_pickled_bestPhraseDict_file = open(p_bestdict_pickle_address, 'rb')
        p_bestPhraseDict = dill.load(p_pickled_bestPhraseDict_file)
        p_pickled_bestPhraseDict_file.close()

    elif blastOption == 'both':
        x_pickled_bestPhraseDict_file = open(x_bestdict_pickle_address, 'rb')
        x_bestPhraseDict = dill.load(x_pickled_bestPhraseDict_file)
        x_pickled_bestPhraseDict_file.close()

        p_pickled_bestPhraseDict_file = open(p_bestdict_pickle_address, 'rb')
        p_bestPhraseDict = dill.load(p_pickled_bestPhraseDict_file)
        p_pickled_bestPhraseDict_file.close()

    # Make the csv file
    csv_address = filename_generator.filename_generator('csv', formatted_TTHERM_ID_list, 
    	clade = clade, blastOption = blastOption, threshold = threshold)
    
    with open(csv_address, 'wb') as csvfile:
        
        infoWriter = csv.writer(csvfile, dialect='excel')

        if len(formatted_TTHERM_ID_list) == 1:
            if blastOption == 'blastx':
                header = ['TTHERM_ID', 'Common.Name', 'Description', 'Gene.Onotology', 'z-score',
                    'BLASTx.Ortholog.Summary', 
                    'BLASTx.Paralog.Summary',
                    'BLASTx.Mixed.Summary',
                    'BLASTx.Mixed.Longest.Common.Phrase', 'cDNA', 'protein']
            
            elif blastOption == 'blastp':
                header = ['TTHERM_ID', 'Common.Name', 'Description', 'Gene.Onotology', 'z-score',
                    'BLASTp.Ortholog.Summary', 
                    'BLASTp.Paralog.Summary',
                    'BLASTp.Mixed.Summary',
                    'BLASTp.Mixed.Longest.Common.Phrase', 'cDNA', 'protein']

            elif blastOption == 'both':
                header = ['TTHERM_ID', 'Common.Name', 'Description', 'Gene.Onotology',  'z-score',
                    'BLASTx.Ortholog.Summary', 
                    'BLASTx.Paralog.Summary',
                    'BLASTx.Mixed.Summary',
                    'BLASTx.Mixed.Longest.Common.Phrase',
                    'BLASTp.Ortholog.Summary', 
                    'BLASTp.Paralog.Summary',
                    'BLASTp.Mixed.Summary',
                    'BLASTp.Mixed.Longest.Common.Phrase', 'cDNA', 'protein']
            
        else:
            # z-scores are not informative in this case.
            if blastOption == 'blastx':
                header = ['TTHERM_ID', 'Common.Name', 'Description', 'Gene.Onotology',
                    'BLASTx.Ortholog.Summary', 
                    'BLASTx.Paralog.Summary',
                    'BLASTx.Mixed.Summary',
                    'BLASTx.Mixed.Longest.Common.Phrase', 'cDNA', 'protein']
            
            elif blastOption == 'blastp':
                header = ['TTHERM_ID', 'Common.Name', 'Description', 'Gene.Onotology',
                    'BLASTp.Ortholog.Summary', 
                    'BLASTp.Paralog.Summary',
                    'BLASTp.Mixed.Summary',
                    'BLASTp.Mixed.Longest.Common.Phrase', 'cDNA', 'protein']

            elif blastOption == 'both':
                header = ['TTHERM_ID', 'Common.Name', 'Description', 'Gene.Onotology',
                    'BLASTx.Ortholog.Summary', 
                    'BLASTx.Paralog.Summary',
                    'BLASTx.Mixed.Summary',
                    'BLASTx.Mixed.Longest.Common.Phrase',
                    'BLASTp.Ortholog.Summary', 
                    'BLASTp.Paralog.Summary',
                    'BLASTp.Mixed.Summary',
                    'BLASTp.Mixed.Longest.Common.Phrase', 'cDNA', 'protein']            
        infoWriter.writerow(header)
        if len(formatted_TTHERM_ID_list) == 1:
            for i in xrange(len(coregs_zscores_cDNA_list)):
                row = []
                key = coregs_zscores_cDNA_list[i].TTHERM_ID
                row.append(coregs_zscores_cDNA_list[i].TTHERM_ID)
                row.append(coregs_zscores_cDNA_list[i].common_name)
                row.append(coregs_zscores_cDNA_list[i].description)
                row.append(coregs_zscores_cDNA_list[i].gene_ontology)
                row.append(coregs_zscores_cDNA_list[i].zscore)
                if blastOption == 'blastx':
                    row = append_summaries_to_csv_row(x_bestPhraseDict, row, key)

                elif blastOption == 'blastp':
                    row = append_summaries_to_csv_row(p_bestPhraseDict, row, key)

                elif blastOption == 'both':
                    row = append_summaries_to_csv_row(x_bestPhraseDict, row, key)
                    row = append_summaries_to_csv_row(p_bestPhraseDict, row, key)

                row.append(coregs_zscores_cDNA_list[i].cDNA)
                row.append(coregs_zscores_cDNA_list[i].protein)
                #print row
                infoWriter.writerow(row)
        else:
            # z-scores are not informative in this case.
            for i in xrange(len(coregs_zscores_cDNA_list)):
                row = []
                key = coregs_zscores_cDNA_list[i].TTHERM_ID
                row.append(coregs_zscores_cDNA_list[i].TTHERM_ID)
                row.append(coregs_zscores_cDNA_list[i].common_name)
                row.append(coregs_zscores_cDNA_list[i].description)
                row.append(coregs_zscores_cDNA_list[i].gene_ontology)
                if blastOption == 'blastx':
                    row = append_summaries_to_csv_row(x_bestPhraseDict, row, key)

                elif blastOption == 'blastp':
                    row = append_summaries_to_csv_row(p_bestPhraseDict, row, key)

                elif blastOption == 'both':
                    row = append_summaries_to_csv_row(x_bestPhraseDict, row, key)
                    row = append_summaries_to_csv_row(p_bestPhraseDict, row, key)

                row.append(coregs_zscores_cDNA_list[i].cDNA)
                row.append(coregs_zscores_cDNA_list[i].protein)
                #print row
                infoWriter.writerow(row)            
    return


def sanitize_database_errors(formatted_TTHERM_ID_list, threshold, 
    syncOption, blastOption, clade):
    """ Check each row of .csv file for "db error" in either the BLASTx
        or BLASTp columns. If "db error" is present, remove the 
        corresponding BLAST profile.
    """
    # pdb.set_trace()
    print 'Sanitizing database errors...'
    logging.info('Sanitizing database errors...')
    # Get csv file adresses
    csv_address = filename_generator.filename_generator('csv', formatted_TTHERM_ID_list, 
    	clade = clade, blastOption = blastOption, threshold = threshold)

    if not os.path.exists(csv_address):
        print 'There is no report for {} from which to sanitize database errors'.format(formatted_TTHERM_ID_list)
        logging.info('There is no report for {} from which to sanitize database errors'.format(formatted_TTHERM_ID_list))
        CoregulationDataHarvester.main()

    with open(csv_address, 'rU') as csvfile:
        reader = csv.reader(csvfile, dialect = 'excel')
        for row in reader:
            
            # Get BLAST file addresses: row[0] is the TTHERM_ID
            blastx_address, drop_blastx_address, reciprocal_blastx_address, drop_reciprocal_blastx_address = \
            filename_generator.filename_generator('blast', [row[0]], clade = clade, blastOption = 'blastx')

            blastp_address, drop_blastp_address, reciprocal_blastp_address, drop_reciprocal_blastp_address = \
            filename_generator.filename_generator('blast', [row[0]], clade = clade, blastOption = 'blastp')
            
            # If the user wants to work with Dropbox, make sure to delete files
            # both from computer and Dropbox, so there is less chance that the
            # user will end up with different versions of BLASTs on the 
            # computer and on the cloud.
            if syncOption != 3:
                if blastOption == 'blastx':
                    if 'db error' in row[5]:
                        # First, attempt to remove local files, then the 
                        # dropbox files. Make sure that program doesn't crash
                        # if the files already don't exist for some reason
                        try:
                            os.remove(blastx_address)
                            print 'Removed local BLASTx profile for %s' \
                                % row[0]
                            logging.info('Removed local BLASTx profile for %s' \
                                % row[0])
                        except:
                            print 'The local BLASTx profile for %s has ' \
                                'already been removed. Moving on...' % row[0]
                            logging.info('The local BLASTx profile for %s has ' \
                                'already been removed. Moving on...' % row[0])
                            pass
                        
                        try:
                            os.remove(reciprocal_blastx_address)
                            print 'Removed local reciprocally-filtered BLASTx profile for %s' \
                                % row[0]
                            logging.info('Removed local reciprocally-filtered BLASTx profile for %s' \
                                % row[0])
                        except:
                            print 'The local reciprocally-BLASTx profile for %s has ' \
                                'already been removed. Moving on...' % row[0]
                            logging.info('The local reciprocally-BLASTx profile for %s has ' \
                                'already been removed. Moving on...' % row[0])
                            pass

                        try:
                            os.remove(drop_blastx_address)
                            print 'Removed dropbox BLASTx profile for %s' \
                                % row[0]
                            logging.info('Removed dropbox BLASTx profile for %s' \
                                % row[0])
                        except:
                            print 'The dropbox BLASTx profile for %s has ' \
                                'already been removed. Moving on...' % row[0]
                            logging.info('The dropbox BLASTx profile for %s has ' \
                                'already been removed. Moving on...' % row[0])

                        try:
                            os.remove(drop_reciprocal_blastx_address)
                            print 'Removed dropbox reciprocally-filtered BLASTx profile for %s' \
                                % row[0]
                            logging.info('Removed dropbox reciprocally-filtered BLASTx profile for %s' \
                                % row[0])
                        except:
                            print 'The dropbox reciprocally-filtered BLASTx profile for %s has ' \
                                'already been removed. Moving on...' % row[0]
                            logging.info('The dropbox reciprocally-filtered BLASTx profile for %s has ' \
                                'already been removed. Moving on...' % row[0])



                elif blastOption == 'blastp':
                    if 'db error' in row[5]:
                        # First, attempt to remove local file, then the 
                        # dropbox file. Make sure that program doesn't crash
                        # if the files already don't exist for some reason
                        try:
                            os.remove(blastp_address)
                            print 'Removed local BLASTp profile for %s' \
                                % row[0]
                            logging.info('Removed local BLASTp profile for %s' \
                                % row[0])
                        except:
                            print 'The local BLASTp profile for %s has ' \
                                'already been removed. Moving on...' % row[0]
                            logging.info('The local BLASTp profile for %s has ' \
                                'already been removed. Moving on...' % row[0])
                            pass

                        try:
                            os.remove(reciprocal_blastp_address)

                            print 'Removed local reciprocally-filtered BLASTp profile for %s' \
                                % row[0]
                            logging.info('Removed local reciprocally-filtered BLASTp profile for %s' \
                                % row[0])
                        except:
                            print 'The local reciprocally-filtered BLASTp profile for %s has ' \
                                'already been removed. Moving on...' % row[0]
                            logging.info('The local reciprocally-filtered BLASTp profile for %s has ' \
                                'already been removed. Moving on...' % row[0])
                            pass


                        
                        try:
                            os.remove(drop_blastp_address)
                            print 'Removed dropbox BLASTp profile for %s' \
                                % row[0]
                            logging.info('Removed dropbox BLASTp profile for %s' \
                                % row[0])
                        except:
                            print 'The dropbox BLASTp profile for %s has ' \
                                'already been removed. Moving on...' % row[0]
                            logging.info('The dropbox BLASTp profile for %s has ' \
                                'already been removed. Moving on...' % row[0])

                        try:
                            os.remove(drop_reciprocal_blastp_address)
                            print 'Removed dropbox reciprocally-filtered BLASTp profile for %s' \
                                % row[0]
                            logging.info('Removed dropbox reciprocally-filtered BLASTp profile for %s' \
                                % row[0])
                        except:
                            print 'The dropbox reciprocally-filtered BLASTp profile for %s has ' \
                                'already been removed. Moving on...' % row[0]
                            logging.info('The dropbox reciprocally-filtered BLASTp profile for %s has ' \
                                'already been removed. Moving on...' % row[0])



                elif blastOption == 'both':
                    if 'db error' in row[5]:
                        try:
                            os.remove(blastx_address)
                            print 'Removed local BLASTx profile for %s' \
                                % row[0]
                            logging.info('Removed local BLASTx profile for %s' \
                                % row[0])
                        except:
                            print 'The local BLASTx profile for %s has ' \
                                'already been removed. Moving on...' % row[0]
                            logging.info('The local BLASTx profile for %s has ' \
                                'already been removed. Moving on...' % row[0])
                            pass

                        try:
                            os.remove(reciprocal_blastx_address)
                            print 'Removed local reciprocally-filtered BLASTx profile for %s' \
                                % row[0]
                            logging.info('Removed local reciprocally-filtered BLASTx profile for %s' \
                                % row[0])

                        except:
                            print 'The local reciprocally-filtered BLASTx profile for %s has ' \
                                'already been removed. Moving on...' % row[0]
                            logging.info('The local reciprocally-filtered BLASTx profile for %s has ' \
                                'already been removed. Moving on...' % row[0])
                            pass

                        try:
                            os.remove(drop_blastx_address)
                            print 'Removed dropbox BLASTx profile for %s' \
                                % row[0]
                            logging.info('Removed dropbox BLASTx profile for %s' \
                                % row[0])
                        except:
                            print 'The dropbox BLASTx profile for %s has ' \
                                'already been removed. Moving on...' % row[0]
                            logging.info('The dropbox BLASTx profile for %s has ' \
                                'already been removed. Moving on...' % row[0])

                        try:
                            os.remove(drop_reciprocal_blastx_address)
                            print 'Removed dropbox reciprocally-filtered BLASTx profile for %s' \
                                % row[0]
                            logging.info('Removed dropbox reciprocally-filtered BLASTx profile for %s' \
                                % row[0])
                        except:
                            print 'The dropbox reciprocally-filtered BLASTx profile for %s has ' \
                                'already been removed. Moving on...' % row[0]
                            logging.info('The dropbox reciprocally-filtered BLASTx profile for %s has ' \
                                'already been removed. Moving on...' % row[0])

                    if 'db error' in row[7]:
                        try:
                            os.remove(blastp_address)
                            print 'Removed local BLASTp profile for %s' \
                                % row[0]
                            logging.info('Removed local BLASTp profile for %s' \
                                % row[0])
                        except:
                            print 'The local BLASTp profile for %s has ' \
                                'already been removed. Moving on...' % row[0]
                            logging.info('The local BLASTp profile for %s has ' \
                                'already been removed. Moving on...' % row[0])
                            pass
                        

                        try:
                            os.remove(reciprocal_blastp_address)
                            print 'Removed local reciprocally-filtered BLASTp profile for %s' \
                                % row[0]
                            logging.info('Removed local reciprocally-filtered BLASTp profile for %s' \
                                % row[0])
                        except:
                            print 'The local reciprocally-filtered BLASTp profile for %s has ' \
                                'already been removed. Moving on...' % row[0]
                            logging.info('The local reciprocally-filtered BLASTp profile for %s has ' \
                                'already been removed. Moving on...' % row[0])
                            pass

                        try:
                            os.remove(drop_blastp_address)
                            print 'Removed dropbox BLASTp profile for %s' \
                                % row[0]
                            logging.info('Removed dropbox BLASTp profile for %s' \
                                % row[0])
                        except:
                            print 'The dropbox BLASTp profile for %s has ' \
                                'already been removed. Moving on...' % row[0]
                            logging.info('The dropbox BLASTp profile for %s has ' \
                                'already been removed. Moving on...' % row[0])
            
                        try:
                            os.remove(drop_reciprocal_blastp_address)
                            print 'Removed dropbox reciprocally-filtered BLASTp profile for %s' \
                                % row[0]
                            logging.info('Removed dropbox reciprocally-filtered BLASTp profile for %s' \
                                % row[0])
                        except:
                            print 'The dropbox reciprocally-filtered BLASTp profile for %s has ' \
                                'already been removed. Moving on...' % row[0]
                            logging.info('The dropbox reciprocally-filtered BLASTp profile for %s has ' \
                                'already been removed. Moving on...' % row[0])



            # If user is not using Dropbox
            elif syncOption == 3:
                if blastOption == 'blastx':
                    if 'db error' in row[5]:
                        try:
                            os.remove(blastx_address)
                            print 'Removed local BLASTx profile for %s' \
                                % row[0]
                            logging.info('Removed local BLASTx profile for %s' \
                                % row[0])
                        except:
                            print 'The local BLASTx profile for %s has ' \
                                'already been removed. Moving on...' % row[0]
                            logging.info('The local BLASTx profile for %s has ' \
                                'already been removed. Moving on...' % row[0])
                            pass

                        try:
                            os.remove(reciprocal_blastx_address)
                            print 'Removed local reciprocally-filtered BLASTx profile for %s' \
                                % row[0]
                            logging.info('Removed local reciprocally-filtered BLASTx profile for %s' \
                                % row[0])
                        except:
                            print 'The local reciprocally-filtered BLASTx profile for %s has ' \
                                'already been removed. Moving on...' % row[0]
                            logging.info('The local reciprocally-filtered BLASTx profile for %s has ' \
                                'already been removed. Moving on...' % row[0])
                            pass


                elif blastOption == 'blastp':
                    if 'db error' in row[5]:
                        try:
                            os.remove(blastp_address)
                            print 'Removed local BLASTp profile for %s' \
                                % row[0]
                            logging.info('Removed local BLASTp profile for %s' \
                                % row[0])
                        except:
                            print 'The local BLASTp profile for %s has ' \
                                'already been removed. Moving on...' % row[0]
                            logging.info('The local BLASTp profile for %s has ' \
                                'already been removed. Moving on...' % row[0])
                            pass
                        

                        try:
                            os.remove(reciprocal_blastp_address)
                            print 'Removed local reciprocally-filtered BLASTp profile for %s' \
                                % row[0]
                            logging.info('Removed local reciprocally-filtered BLASTp profile for %s' \
                                % row[0])
                        except:
                            print 'The local reciprocally-filtered BLASTp profile for %s has ' \
                                'already been removed. Moving on...' % row[0]
                            logging.info('The local reciprocally-filtered BLASTp profile for %s has ' \
                                'already been removed. Moving on...' % row[0])
                            pass


                elif blastOption == 'both':
                    if 'db error' in row[5]:
                        try:
                            os.remove(blastx_address)
                            print 'Removed local BLASTx profile for %s' \
                                % row[0]
                            logging.info('Removed local BLASTx profile for %s' \
                                % row[0])
                        except:
                            print 'The local BLASTx profile for %s has ' \
                                'already been removed. Moving on...' % row[0]
                            logging.info('The local BLASTx profile for %s has ' \
                                'already been removed. Moving on...' % row[0])
                            pass


                        try:
                            os.remove(reciprocal_blastx_address)
                            print 'Removed local reciprocally-filtered BLASTx profile for %s' \
                                % row[0]
                            logging.info('Removed local reciprocally-filtered BLASTx profile for %s' \
                                % row[0])
                        except:
                            print 'The local reciprocally-filtered BLASTx profile for %s has ' \
                                'already been removed. Moving on...' % row[0]
                            logging.info('The local reciprocally-filtered BLASTx profile for %s has ' \
                                'already been removed. Moving on...' % row[0])
                            pass


                    if 'db error' in row[7]:
                        try:
                            os.remove(blastp_address)
                            print 'Removed local BLASTp profile for %s ' \
                                % row[0]
                            logging.info('Removed local BLASTp profile for %s ' \
                                % row[0])
                        except:
                            print 'The local BLASTp profile for %s has ' \
                                'already been removed. Moving on...' % row[0]
                            logging.info('The local BLASTp profile for %s has ' \
                                'already been removed. Moving on...' % row[0])
                            pass
    
                    # if 'db error' in row[7]:
                        try:
                            os.remove(reciprocal_blastp_address)
                            print 'Removed local reciprocally-filtered BLASTp profile for %s ' \
                                % row[0]
                            logging.info('Removed local reciprocally-filtered BLASTp profile for %s ' \
                                % row[0])
                        except:
                            print 'The local reciprocally-filtered BLASTp profile for %s has ' \
                                'already been removed. Moving on...' % row[0]
                            logging.info('The local reciprocally-filtered BLASTp profile for %s has ' \
                                'already been removed. Moving on...' % row[0])
                            pass


    return


def CoregFilesIO(formatted_TTHERM_ID_list, threshold, owOption, 
    syncOption, blastOption, clade):
    """ Manage all of the above functions.
    """

    if owOption == 4:
        sanitize_database_errors(
            formatted_TTHERM_ID_list, threshold, syncOption, blastOption, clade)
    else:
        print
        print 'Initializing homology analysis'
        logging.info('Initializing homology analysis')
        dictionary_work(formatted_TTHERM_ID_list, threshold, owOption, 
            syncOption, blastOption, clade)
        make_CSV(formatted_TTHERM_ID_list, threshold, blastOption, clade)
        print
        print 'Analysis complete'
        logging.info('Analysis complete')

    return

