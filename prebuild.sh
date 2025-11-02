#!/bin/bash

# Update pip and install build essentials
python -m pip install --upgrade pip
pip install --upgrade setuptools wheel

# Install base requirements needed for building
pip install setuptools wheel build

# Install the project requirements
pip install -r requirements.txt

# Verify installations
python -c "import discord; print('discord.py version:', discord.__version__)"