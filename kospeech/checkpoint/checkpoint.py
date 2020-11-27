# -*- coding: utf-8 -*-
# Soohwan Kim, Seyoung Bae, Cheolhwang Won.
# @ArXiv : KoSpeech: Open-Source Toolkit for End-to-End Korean Speech Recognition
# This source code is licensed under the Apache 2.0 License license found in the
# LICENSE file in the root directory of this source tree.

import os
import time
import shutil
import torch
import torch.nn as nn
from kospeech.utils import logger
from kospeech.data.data_loader import SpectrogramDataset
from kospeech.models.las.model import ListenAttendSpell
from kospeech.optim.optimizer import Optimizer


class Checkpoint(object):
    """
    The Checkpoint class manages the saving and loading of a model during training.
    It allows training to be suspended and resumed at a later time (e.g. when running on a cluster using sequential jobs).
    To make a checkpoint, initialize a Checkpoint object with the following args; then call that object's save() method
    to write parameters to disk.

    Args:
        model (nn.Module): model being trained
        optimizer (torch.optim): stores the state of the optimizer
        trainset_list (list): list of trainset
        validset (kospeech.data.data_loader.SpectrogramDataset): validation dataset
        epoch (int): current epoch (an epoch is a loop through the full training data)

    Attributes:
        CHECKPOINT_DIR_NAME (str): name of the checkpoint directory
        TRAINER_STATE_NAME (str): name of the file storing trainer states
        SAVE_PATH (str): path of save directory
        MODEL_NAME (str): name of the file storing model
    """

    CHECKPOINT_DIR_NAME = 'checkpoints'
    TRAINER_STATE_NAME = 'trainer_states.pt'
    SAVE_PATH = '../data/checkpoint'
    MODEL_NAME = 'model.pt'

    def __init__(
            self,
            model: nn.Module = None,                   # model being trained
            optimizer: Optimizer = None,               # stores the state of the optimizer
            trainset_list: list = None,                # list of trainset
            validset: SpectrogramDataset = None,       # validation dataset
            epoch: int = None                          # current epoch is a loop through the full training data
    ) -> None:
        self.model = model
        self.optimizer = optimizer
        self.trainset_list = trainset_list
        self.validset = validset
        self.epoch = epoch

    def save(self):
        """
        Saves the current model and related training parameters into a subdirectory of the checkpoint directory.
        The name of the subdirectory is the current local time in Y_M_D_H_M_S format.
        """
        date_time = time.strftime('%Y_%m_%d_%H_%M_%S', time.localtime())
        path = os.path.join(self.SAVE_PATH, self.CHECKPOINT_DIR_NAME, date_time)

        if os.path.exists(path):
            shutil.rmtree(path)  # delete path dir & sub-files
        os.makedirs(path)

        trainer_states = {
            'optimizer': self.optimizer,
            'trainset_list': self.trainset_list,
            'validset': self.validset,
            'epoch': self.epoch
        }
        torch.save(trainer_states, os.path.join(path, self.TRAINER_STATE_NAME))
        torch.save(self.model, os.path.join(path, self.MODEL_NAME))
        logger.info('save checkpoints\n%s\n%s'
                    % (os.path.join(path, self.TRAINER_STATE_NAME),
                       os.path.join(path, self.MODEL_NAME)))

    def load(self, path):
        """
        Loads a Checkpoint object that was previously saved to disk.

        Args:
            path (str): path to the checkpoint subdirectory

        Returns:
            checkpoint (Checkpoint): checkpoint object with fields copied from those stored on disk
       """
        logger.info('load checkpoints\n%s\n%s'
                    % (os.path.join(path, self.TRAINER_STATE_NAME),
                       os.path.join(path, self.MODEL_NAME)))

        if torch.cuda.is_available():
            resume_checkpoint = torch.load(os.path.join(path, self.TRAINER_STATE_NAME))
            model = torch.load(os.path.join(path, self.MODEL_NAME))

        else:
            resume_checkpoint = torch.load(os.path.join(path, self.TRAINER_STATE_NAME), map_location=lambda storage, loc: storage)
            model = torch.load(os.path.join(path, self.MODEL_NAME), map_location=lambda storage, loc: storage)

        if isinstance(model, ListenAttendSpell):
            if isinstance(model, nn.DataParallel):
                model.module.flatten_parameters()  # make RNN parameters contiguous
            else:
                model.flatten_parameters()

        return Checkpoint(
            model=model, optimizer=resume_checkpoint['optimizer'], epoch=resume_checkpoint['epoch'],
            trainset_list=resume_checkpoint['trainset_list'],
            validset=resume_checkpoint['validset']
        )

    def get_latest_checkpoint(self):
        """
        returns the path to the last saved checkpoint's subdirectory.
        Precondition: at least one checkpoint has been made (i.e., latest checkpoint subdirectory exists).
        """
        checkpoints_path = os.path.join(self.SAVE_PATH, self.CHECKPOINT_DIR_NAME)
        sorted_listdir = sorted(os.listdir(checkpoints_path), reverse=True)
        return os.path.join(checkpoints_path, sorted_listdir[0])
