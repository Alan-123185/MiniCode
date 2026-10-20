from fastapi.params import Depends
from config.chatConfig import chat_config
from config.dependencies import get_db, get_graph
from mapper.modelMapper import modelMapper
from mapper.sessionMapper import sessionMapper
from mapper.fileMapper import FileOperationMapper
from mapper.OperationGroupMapper import operatinoGroupMapper
from service.modelService import modelService
from service.workplaceService import WorkplaceService
from service.chatService import ChatService
from service.sessionService import sessionService



def get_session_service(db= Depends(get_db),graph=Depends(get_graph)) -> sessionService:
    fileMapper = FileOperationMapper(db)
    sessionmapper = sessionMapper(db)
    operationgroupMapper = operatinoGroupMapper(db)
    return sessionService(graph, fileMapper, sessionmapper, operationgroupMapper)




def get_chat_service(db=Depends(get_db),graph=Depends(get_graph)) -> ChatService:
    sessionmapper = sessionMapper(db)
    fileMapper = FileOperationMapper(db)
    operationggroupmapper = operatinoGroupMapper(db)
    return ChatService(
        graph=graph,
        chat_config=chat_config,
        sessionMapper=sessionmapper,
        fileMapper=fileMapper,
        operationgroupMapper=operationggroupmapper,
    )


def get_workplace_service(db = Depends(get_db),graph=Depends(get_graph)) -> WorkplaceService:
    sessionmapper = sessionMapper(db)
    return WorkplaceService(graph=graph, sessionMappper=sessionmapper)



def get_model_service(db = Depends(get_db)) -> modelService:
    modelmapper = modelMapper(db)
    return modelService(modelmapper)
