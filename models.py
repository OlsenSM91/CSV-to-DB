from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

Base = declarative_base()

class Client(Base):
    __tablename__ = 'clients'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    workstations = relationship('Workstation', back_populates='client')

class Workstation(Base):
    __tablename__ = 'workstations'
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('clients.id'))
    computer_name = Column(String)         # "Computer Name"
    ram_gb = Column(String)                # "RAM_GB"
    processor_name = Column(String)        # "Processor Name"
    diskspace_remaining_gb = Column(String) # "DiskSpaceRemaining_GB"
    status = Column(String, default='Pending Upgrade')
    technician = Column(String, default='')
    notes = Column(Text, default='')
    client = relationship('Client', back_populates='workstations')
