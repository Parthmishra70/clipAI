"""
Scheduler to run daily tasks at 4 AM
This can be deployed as a background service
"""
import os
import sys
from manage import *
from nameExtractor import name_saver


# Firstly run this at 4 AM to ingest data into the database (Update the database)
ingest_data()

# run this after ingestion finished (Update the CSV file)
name_saver()

print("Scheduler tasks completed.")