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
__version__ = '1.2.1'

"""
    Overall CDH process
    1) Ask for query
        Defined by:
            Gene id
            Threshold for strength of co-regulation
            How to process data and files
            Which BLAST algorithm to use (BLASTp or BLASTx)
            Which taxa to BLAST against
    2) Find set of co-regulated genes from the TetraFGD
    3) Find sequences and descriptions from TGD
    4) Forward and reciprocal BLASTs
        Separate predicted orthologs, paralogs, and uninformative homologs
    5) Do phrase analysis of ortholog and paralog hit definitions
    6) Build report for the whole list of co-regulated genes.

"""


# imports
import sys
import os
import platform
import WebdriverModule as WebMod
import CoregFilesIO
import time
import logging
import filename_generator

# constants

# functions

def main():

    """ Currently just initializing variables and running the functions

    """
    try:
        # I am using this try-except setup so that the executable doesn't
        # simply crash and close if something goes wrong, and the user
        # is able to discern what happened.
        print

        searchInput = raw_input(
            'Please enter one or multiple TTHERM_IDs (for cross analysis), separated by commas: ').strip()

        # Easter egg--thanks for reading my code! :-)
        if 'I seek the Holy Grail' in searchInput:
            print 'AIIIIEIEEEEEGGGHGHGHGHGGHGHGHHGGHHGghdghghghghghg *sploosh*'
            main()

        elif 'license' in searchInput:
            print """
        Coregulation Data Harvester--A tool for organizing and predicting Tetrahymena 
        thermophila gene annotations 

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
            main()

        TTHERM_ID_list = searchInput.split(',')
        formatted_TTHERM_ID_list = []
        for TTHERM in TTHERM_ID_list:
            if 'TTHERM_' in TTHERM:
                formatted_TTHERM_ID_list.append(TTHERM.strip())
            else:
                print 'One or more of your queries is not formatted properly.'
                print 'Please make sure each entry is in the format TTHERM_XXXXXXXX'
                print
                main()

        log_address = filename_generator.filename_generator('log', formatted_TTHERM_ID_list)
        logging.basicConfig(filename = log_address, level=logging.INFO)

        print

        threshold = float(input(
            '''To determine how many of the co-regulated genes should be
subject to homology analysis, please enter the lower-bound
z-score for the strength of co-regulation. If you have 
entered multiple TTHERM_IDs, this number will be used for all of them: '''))

        print

        owOption = input(
            '''How should I process each gene in your query?
                (1) overwrite all associated files,
                (2) overwrite just the BLASTs and analysis 
                    as well as fill in any missing files,
                (3) overwrite only the analysis and fill in any 
                    missing files,
                (4) sanitize database errors, or
                (5) run only the FGD/TGD search
                Your choice: ''')   
        
        # Check for valid input
        if owOption not in [1,2,3,4,5]:
            print
            print "I'm sorry, I do not understand your input. Please try again."
            print
            main()

        print

        syncOption = input(
            '''Send to Dropbox? 
                (1) Yes, and also write new results locally.
                (2) Yes, but do not write new results locally. 
                    Remark: if you chose option (2) or (3) above, 
                    some files may still be synchronized
                    between the Dropbox and local directories.
                (3) No, run everything locally.
                Your choice: ''')
        
        # Make sure that a valid input was given
        if syncOption not in [1,2,3]:
            print "I'm sorry, that is an invalid input. Please start a new query."
            main()
        
        # User only wants to run the FGD/TGD search
        elif owOption == 5:
            print 'Run started:', time.ctime()
            logging.info('Run started: {}'.format(time.ctime()))
            WebMod.WebMod(
                formatted_TTHERM_ID_list, threshold, owOption, syncOption, blastOption=None, entrez=None, clade=None)
            print 'Run ended:', time.ctime()
            logging.info('Run ended: {}'.format(time.ctime()))
            print
            cont = raw_input(
                "Do you want to start another search (y/n)? ")[0].lower()
            
            if cont == 'y':
                main()

            elif cont == 'n':
                sys.exit()

            else:
                print "I'm afraid I didn't understand that, so I'm assuming that you "\
                    "want to quit."
                sys.exit()

            return

        print
        # User wants to run the whole thing
        # Ask for what kind of BLAST to run
        blastOption = input(
            '''What kind of NCBI BLAST algorithm would you like to run?
                (1) BLASTp,
                (2) BLASTx, or 
                (3) both?
                Your choice: ''')

        # Check for valid input
        if blastOption not in [1, 2, 3]:
            print
            print "I'm sorry, I didn't understand that input. Please try again."
            print
            main()

        if blastOption == 1:
            blastOption = 'blastp'

        elif blastOption == 2:
            blastOption = 'blastx'

        elif blastOption == 3:
            blastOption = 'both'

        print

        # I want to let the user be able to decide in which taxa to run the BLAST
        # searches, since different approaches can be informative in different
        # ways. The 'entrez' variable is entered into the NCBIWWW.qblast functions
        # in the WebMod module. The 'clade' variable is used to denote what sort
        # of search was used in dependent file names (e.g. BLAST data files and 
        # reports).

        entrezOption = input(
            '''You may choose whether to look for homologs in all organisms
outside the Ciliates, only within the Ciliates, everywhere, 
or custom entrez query:
                (1) BLAST outside the Ciliates
                (2) BLAST within the Ciliates
                (3) BLAST everywhere
                (4) Custom (please use the NCBI guidelines and 
                    instructions for formulating the entrez query)
                Your choice: ''')

        if entrezOption not in [1,2,3,4]:
            print
            print "I'm sorry, I do not understand your input. Please try again"
            print

        elif entrezOption in [1,2,3,4]:
            if entrezOption == 1:
                entrez = 'NOT Ciliata'
                clade = 'NOTciliates'
            elif entrezOption == 2:
                entrez = 'Ciliata'
                clade = 'ciliates'
            elif entrezOption == 3:
                entrez = '(none)'
                clade = 'all'
            elif entrezOption == 4:
                print
                entrez = raw_input(
                    'Please enter your custom entrez query: ')
                print
                clade = raw_input(
                    '''Please enter a short description of the taxonomic group
that your entrez query defines, such as NOTciliates or opisthokonths.
These descriptions should not include any spaces or punctuation, as
they will be used in file names. Take care to use something succinct
and informative: ''')

        print
        print 'Run started:', time.ctime()
        logging.info('Run started: {}'.format(time.ctime()))
        print
        if owOption == 1 or owOption == 2 or owOption == 3:
            WebMod.WebMod(formatted_TTHERM_ID_list, threshold, owOption, 
                syncOption, blastOption, entrez, clade)
            
            CoregFilesIO.CoregFilesIO(formatted_TTHERM_ID_list, threshold, owOption, 
                syncOption, blastOption, clade)

        elif owOption == 4:
            # First sanitize, using the given parameters
            CoregFilesIO.CoregFilesIO(
                formatted_TTHERM_ID_list, threshold, owOption, syncOption, blastOption, clade)

            # Then replace the removed files, using the same TTHERM_ID, same
            # threshold, owOption = 3 (so that nothing is needlessly overwritten),
            # same syncOption, same blastOption, same clade.
            WebMod.WebMod(formatted_TTHERM_ID_list, threshold, 3, syncOption, 
                blastOption, entrez, clade)

            # Then reanalyze the data. Here the owOption doesn't matter, so I'll 
            # just keep it at 3 for consistency and ease of understanding the 
            # intention

            CoregFilesIO.CoregFilesIO(
                formatted_TTHERM_ID_list, threshold, 3, syncOption, blastOption, clade)




        print
        print 'Run ended:', time.ctime()
        logging.info('Run ended: {}'.format(time.ctime()))
        print
        cont = raw_input(
            "Do you want to start another search (y/n)? ")[0].lower()
        
        if cont == 'y':
            main()

        elif cont == 'n':
            sys.exit()

        else:
            print "I'm afraid I didn't understand that, so I'm assuming that you "\
                "want to quit."
            sys.exit()

            # return

    except SystemExit:
        sys.exit()
    except IOError:
        print
        print "There was an error. Are you sure that you are not trying to overwrite a report that is currently open?"
        print sys.exc_info()
        print
        cont = raw_input(
        "Do you want to start another search (y/n)? ")[0].lower()
    
        if cont == 'y':
            main()

        elif cont == 'n':
            sys.exit()

        else:
            print "I'm afraid I didn't understand that, so I'm assuming that you "\
                "want to quit."
            sys.exit()

    except:
        print
        print "There was an unexpected error:", sys.exc_info()
        print
        cont = raw_input(
        "Do you want to start another search (y/n)? ")[0].lower()
    
        if cont == 'y':
            main()

        elif cont == 'n':
            sys.exit()

        else:
            print "I'm afraid I didn't understand that, so I'm assuming that you "\
                "want to quit."
            sys.exit()


if (__name__ == "__main__"):
    print
    print """Coregulation Data Harvester Copyright (C) 2015-2017 Lev M Tsypin
This program comes with ABSOLUTELY NO WARRANTY.
This is free software, and you are welcome to redistribute it
under certain conditions.

For details, see source code or contact the author.

If you would like to see a print out of the license, enter "license" into the first prompt.
    """
    print
    print 'Welcome to the Coregulation Data Harvester for T. thermophila!'
    print
    if platform.system() == 'Darwin':
        ########## MAC DISTRIBUTION ##########
        print 'Your reports will be written to "Documents/'\
            'CoregulationDataHarvester/csvFiles" '\
            'in your "Home" directory. You can use Excel or an ' \
            'equivalent program to view the data.'

    elif platform.system() == 'Windows':
        ########## WIN DISTRIBUTION ##########
        print "Your reports will be located in 'Documents/" \
            "CoregulationDataHarvester/csvFiles'. You can use Excel or an " \
            "equivalent program to view the data."

    elif platform.system() == 'Linux':
        ########## UNIX (UBUNTU) DISTRIBUTION ##########
        print "Your reports will be written to './csvFiles'."

    else:
        print "You seem to be running a system that is not Windows, modern "\
            "Mac OS (Darwin), or Linux... I doubt that my program is compatible. " \
            "Please try again on a supported system"
        sys.exit()

    main()






