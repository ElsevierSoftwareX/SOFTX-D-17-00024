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

import sys
import os
import platform
if platform.system() == 'Windows':
    from win32com.shell import shell, shellcon


def filename_generator(mode, formatted_TTHERM_ID_list, clade = '', blastOption = '', threshold = ''):
    '''
    mode is the sort of file address that you want to get out. Options:
    mode = 'coregs_zscores'
    mode = 'blast'
    mode = 'csv'
    mode = 'best_phrase_dict'
    mode = 'homologue_dict'
    mode = 'log'
    '''
    # Filenames will include all the TTHERMs that went into making them
    TTHERM_ID = '_'.join(formatted_TTHERM_ID_list)
    # coregs-zscore pickled files:
    if mode == 'coregs_zscores':
        if platform.system() == 'Darwin':
            ######### MAC DISTRO ###########
            pickle_dir_address = os.path.expanduser(
                r'~/Library/CoregulationDataHarvester/pickledData/')
            drop_pickle_dir_address = os.path.expanduser(
                r'~/Dropbox/CoregulationDataHarvester/pickledData')
            pickle_address = os.path.join(pickle_dir_address,
                r'coreg_list_for_%s.p' % TTHERM_ID)
            drop_pickle_address = os.path.join(drop_pickle_dir_address,
                r'coreg_list_for_%s.p' % TTHERM_ID)

        elif platform.system() == 'Windows':
            ######### WIN DISTRO ############
            pickle_dir_address = os.path.join(
                shell.SHGetFolderPath(
                    0, shellcon.CSIDL_LOCAL_APPDATA, None, 0),
                r'CoregulationDataHarvester/pickledData/')
            drop_pickle_dir_address = os.path.join(
                shell.SHGetFolderPath(
                    0, shellcon.CSIDL_PROFILE, None, 0),
                r'Dropbox/CoregulationDataHarvester/pickledData/')
            pickle_address = os.path.join(pickle_dir_address,
                r'coreg_list_for_%s.p' % TTHERM_ID)
            drop_pickle_address = os.path.join(drop_pickle_dir_address,
                r'coreg_list_for_%s.p' % TTHERM_ID)   

        elif platform.system() == 'Linux':
            ########## UNIX DISTRO ##########
            pickle_dir_address = os.path.abspath(r'pickledData/')
            drop_pickle_dir_address = os.path.expanduser(
                r'~/Dropbox/CoregulationDataHarvester/pickledData')
            pickle_address = os.path.join(pickle_dir_address,
                r'coreg_list_for_%s.p' % TTHERM_ID)
            drop_pickle_address = os.path.join(drop_pickle_dir_address,
                r'coreg_list_for_%s.p' % TTHERM_ID)

        if not os.path.exists(pickle_dir_address):
            os.makedirs(pickle_dir_address)

        return pickle_address, drop_pickle_address

    elif mode == 'blast':

        if platform.system() == 'Darwin':
            ######### MAC DISTRO #############
            # file addresses for plain BLAST results
            blast_dir_address = os.path.expanduser(
                r'~/Library/CoregulationDataHarvester/BLASTresults/')

            reciprocal_dir_address = os.path.expanduser(
                r'~/Library/CoregulationDataHarvester/reciprocalBLASTresults/')

            drop_blast_dir_address = os.path.expanduser(
                    r'~/Dropbox/CoregulationDataHarvester/BLASTresults/')

            blast_address = os.path.expanduser(
                    r'~/Library/CoregulationDataHarvester/'\
                        'BLASTresults/%s_%s_%s.XML' \
                            % (TTHERM_ID, clade, blastOption))

            drop_blast_address = os.path.expanduser(
                    r'~/Dropbox/CoregulationDataHarvester/'\
                        'BLASTresults/%s_%s_%s.XML' \
                            % (TTHERM_ID, clade, blastOption))

            # File addresses for BLAST results after reciprocal filtering
            # This is the same pattern for all distros
            reciprocal_blast_address = os.path.expanduser(
                    r'~/Library/CoregulationDataHarvester/'\
                        'reciprocalBLASTresults/%s_%s_%s_reciprocal.XML' \
                            % (TTHERM_ID, clade, blastOption))

            drop_reciprocal_blast_address = os.path.expanduser(
                    r'~/Dropbox/CoregulationDataHarvester/'\
                        'reciprocalBLASTresults/%s_%s_%s_reciprocal.XML' \
                            % (TTHERM_ID, clade, blastOption))


        elif platform.system() == 'Windows':
            ######### WIN DISTRO #############
            blast_dir_address = os.path.join(shell.SHGetFolderPath(
                0, shellcon.CSIDL_LOCAL_APPDATA, None, 0), 
                r'CoregulationDataHarvester/BLASTresults/')

            reciprocal_dir_address = os.path.join(shell.SHGetFolderPath(
                0, shellcon.CSIDL_LOCAL_APPDATA, None, 0), 
                r'CoregulationDataHarvester/reciprocalBLASTresults/')

            drop_blast_dir_address = os.path.join(
                    shell.SHGetFolderPath(
                        0, shellcon.CSIDL_PROFILE, None, 0),
                    r'Dropbox/CoregulationDataHarvester/BLASTresults/')

            blast_address = os.path.join(
                shell.SHGetFolderPath(
                    0,shellcon.CSIDL_LOCAL_APPDATA,None,0), 
                r'CoregulationDataHarvester/BLASTresults/',
                r'%s_%s_%s.XML' % (TTHERM_ID, clade, blastOption))

            drop_blast_address = os.path.join(
                shell.SHGetFolderPath(
                    0,shellcon.CSIDL_PROFILE,None,0), 
                r'Dropbox/CoregulationDataHarvester/BLASTresults/',
                r'%s_%s_%s.XML' % (TTHERM_ID, clade, blastOption))

            reciprocal_blast_address = os.path.join(
                shell.SHGetFolderPath(
                    0,shellcon.CSIDL_LOCAL_APPDATA,None,0), 
                r'CoregulationDataHarvester/reciprocalBLASTresults/',
                r'%s_%s_%s_reciprocal.XML' % (TTHERM_ID, clade, blastOption))

            drop_reciprocal_blast_address = os.path.join(
                shell.SHGetFolderPath(
                    0,shellcon.CSIDL_PROFILE,None,0), 
                r'Dropbox/CoregulationDataHarvester/reciprocalBLASTresults/',
                r'%s_%s_%s_reciprocal.XML' % (TTHERM_ID, clade, blastOption))

        elif platform.system() == 'Linux':
            ########## UNIX DISTRO ############
            blast_dir_address = os.path.abspath(r'BLASTresults/')

            reciprocal_dir_address = os.path.abspath(r'reciprocalBLASTresults')

            drop_blast_dir_address = os.path.expanduser(
                    r'~/Dropbox/CoregulationDataHarvester/BLASTresults/')
            blast_address = os.path.abspath(
                r'BLASTresults/%s_%s_%s.XML' \
                    % (TTHERM_ID, clade, blastOption))

            drop_blast_address = os.path.expanduser(
                r'~/Dropbox/CoregulationDataHarvester/'\
                    'BLASTresults/%s_%s_%s.XML' \
                        % (TTHERM_ID, clade, blastOption))

            reciprocal_blast_address = os.path.abspath(
                r'reciprocalBLASTresults/%s_%s_%s_reciprocal.XML' \
                    % (TTHERM_ID, clade, blastOption))

            drop_reciprocal_blast_address = os.path.expanduser(
                r'~/Dropbox/CoregulationDataHarvester/'\
                    'reciprocalBLASTresults/%s_%s_%s_reciprocal.XML' \
                        % (TTHERM_ID, clade, blastOption))

        # Make local folder if it doesn't exist
        if not os.path.exists(blast_dir_address):
            os.makedirs(blast_dir_address)

        if not os.path.exists(reciprocal_dir_address):
        	os.makedirs(reciprocal_dir_address)

        return blast_address, drop_blast_address, reciprocal_blast_address, drop_reciprocal_blast_address

    elif mode == 'csv':
        # Get csv file adresses
        if platform.system() == 'Darwin':
            ######### MAC DISTRO #############
            csv_dir_address = os.path.expanduser(
                r'~/Documents/CoregulationDataHarvester/csvFiles')

            csv_address = os.path.join(csv_dir_address, 
                r'coreg_info_for_%s_%s_%s_%s.csv' \
                    % (TTHERM_ID, clade, blastOption, threshold))

        elif platform.system() == 'Windows':
            ######### WIN DISTRO #############
            csv_dir_address = os.path.join(
                shell.SHGetFolderPath(0, shellcon.CSIDL_PERSONAL, None, 0),
                r'CoregulationDataHarvester/csvFiles')  
            
            csv_address = os.path.join(csv_dir_address,
                r'coreg_info_for_%s_%s_%s_%s.csv' \
                    % (TTHERM_ID, clade, blastOption, threshold))

        elif platform.system() == 'Linux':
            ########## UNIX DISTRO ############
            csv_dir_address = os.path.abspath(r'csvFiles')
            
            csv_address = os.path.join(csv_dir_address,
                r'coreg_info_for_%s_%s_%s_%s.csv' \
                % (TTHERM_ID, clade, blastOption, threshold))

        if not os.path.exists(csv_dir_address):
            os.makedirs(csv_dir_address)

        return csv_address

    elif mode == 'best_phrase_dict':
        # NOTE: RIGHT NOW DICTIONARY WORK AND MAKE CSV USE DIFFERENT NOTATIONS WITH THESE FILES
        if platform.system() == 'Darwin':
            ######## MAC DISTRO ##############
            x_pickled_bestPhraseDict_address = os.path.expanduser(
                r'~/Library/CoregulationDataHarvester/pickledData/'\
                'best_phrase_dict_for_%s_%s_%s.p' \
                    % (TTHERM_ID, "blastx", threshold))
            p_pickled_bestPhraseDict_address = os.path.expanduser(
                r'~/Library/CoregulationDataHarvester/pickledData/'\
                'best_phrase_dict_for_%s_%s_%s.p' \
                    % (TTHERM_ID, "blastp", threshold))

        elif platform.system() == 'Windows':
            ######## WIN DISTRO ##############
            x_pickled_bestPhraseDict_address = os.path.join(
                shell.SHGetFolderPath(0, shellcon.CSIDL_LOCAL_APPDATA, None, 0),
                r'CoregulationDataHarvester/pickledData/',
                r'best_phrase_dict_for_%s_%s_%s.p' \
                    % (TTHERM_ID, "blastx", threshold))
            p_pickled_bestPhraseDict_address = os.path.join(
                shell.SHGetFolderPath(0, shellcon.CSIDL_LOCAL_APPDATA, None, 0),
                r'CoregulationDataHarvester/pickledData/',
                r'best_phrase_dict_for_%s_%s_%s.p' \
                    % (TTHERM_ID, "blastp", threshold))

        elif platform.system() == 'Linux':
            x_pickled_bestPhraseDict_address = os.path.abspath(
                r'pickledData/best_phrase_dict_for_%s_%s_%s.p' \
                    % (TTHERM_ID, "blastx", threshold))
            p_pickled_bestPhraseDict_address = os.path.abspath(
                r'pickledData/best_phrase_dict_for_%s_%s_%s.p' \
                    % (TTHERM_ID, "blastp", threshold))

        return p_pickled_bestPhraseDict_address, x_pickled_bestPhraseDict_address

    elif mode == 'homologue_dict':
        if platform.system() == 'Darwin':
            ############ FOR MAC DISTRIBUTION ##############
            x_homodict_pickle_address = os.path.expanduser(
                r'~/Library/CoregulationDataHarvester/pickledData/'\
                    'homologue_dict_for_%s_%s_%s.p' \
                        % (TTHERM_ID, "blastx", threshold))
            p_homodict_pickle_address = os.path.expanduser(
                r'~/Library/CoregulationDataHarvester/pickledData/'\
                    'homologue_dict_for_%s_%s_%s.p' \
                        % (TTHERM_ID, "blastp", threshold))

        elif platform.system() == 'Windows':
            ############ FOR WIN DISTRIBUTION ##############
            x_homodict_pickle_address = os.path.join(
                shell.SHGetFolderPath(0, shellcon.CSIDL_LOCAL_APPDATA, None, 0),
                r'CoregulationDataHarvester/pickledData/',
                r'homologue_dict_for_%s_%s_%s.p' \
                    % (TTHERM_ID, "blastx", threshold))
            p_homodict_pickle_address = os.path.join(
                shell.SHGetFolderPath(0, shellcon.CSIDL_LOCAL_APPDATA, None, 0),
                r'CoregulationDataHarvester/pickledData/',
                r'homologue_dict_for_%s_%s_%s.p' \
                    % (TTHERM_ID, "blastp", threshold))
        
        elif platform.system() == 'Linux':
            ############ FOR UNIX (UBUNTU) DISTRIBUTION ###############
            x_homodict_pickle_address = os.path.abspath(
                 r'pickledData/homologue_dict_for_%s_%s_%s.p' \
                 % (TTHERM_ID, "blastx", threshold))
            p_homodict_pickle_address = os.path.abspath(
                 r'pickledData/homologue_dict_for_%s_%s_%s.p' \
                 % (TTHERM_ID, "blastp", threshold))

        return p_homodict_pickle_address, x_homodict_pickle_address

    elif mode == 'log':
        log_dir = os.path.abspath('./CDH_logs')
        log_address = os.path.join(log_dir, '{}.log'.format(TTHERM_ID))

        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        return log_address



