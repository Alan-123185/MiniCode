from fastapi.params import Depends
from config.chatConfig import chat_config
from config.dependencies import get_db
from mapper.database import DataBase
from mapper.modelMapper import modelMapper
from mapper.sessionMapper import sessionMapper
from mapper.fileMapper import FileOperationMapper
from mapper.OperationGroupMapper import operatinoGroupMapper
from service.modelService import modelService
from service.workplaceService import WorkplaceService
from service.chatService import ChatService
from service.sessionService import sessionService

def get_session_service(db:DataBase=Depends(get_db)) -> sessionService:
    from graphs.chat_graph import graph
    operationggroupmapper= operatinoGroupMapper(db)
    fileMapper=FileOperationMapper(db)
    sessionmapper= sessionMapper(db)
    return sessionService(graph, fileMapper,operationggroupmapper,sessionmapper)

def get_chat_service(db:DataBase=Depends(get_db)) -> ChatService:
    from graphs.chat_graph import graph
    sessionmapper = sessionMapper(db)
    fileMapper=FileOperationMapper(db)
    operationggroupmapper= operatinoGroupMapper(db)
    return ChatService(graph=graph, chat_config=chat_config,sessionMapper=sessionmapper,fileMapper=fileMapper,operationgroupMapper=operationggroupmapper)

def get_workplace_service(db:DataBase=Depends(get_db)) -> WorkplaceService:
    from graphs.chat_graph import graph
    sessionmapper = sessionMapper(db)
    return WorkplaceService(graph=graph, sessionMappper=sessionmapper)

def get_model_service(db:DataBase=Depends(get_db)) -> modelService:
    modelmapper=modelMapper(db)
    return modelService(modelmapper)
