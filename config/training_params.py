                       
"""
Centraliza os hiperparâmetros e configurações para os scripts de treinamento.
"""

YOLO_CONFIG = {
                               
    "IMG_SIZE": 320,
    "NUM_EPOCHS": 10,
    "PATIENCE_EPOCHS": 100,
    "BATCH_SIZE": 16,
    "OPTIMIZER": "Adam",
    "DATASETS_TO_TRAIN": ['aquarium_pretrain','FishInvSplit','unificacaoDosOceanos'],

    "TRAINING_JOBS": [
       {'modelo': 'YOLOv5n', 'base_model': 'yolov5n.pt'},
        {'modelo': 'YOLOv5s', 'base_model': 'yolov5s.pt'},
        {'modelo': 'YOLOv5m', 'base_model': 'yolov5m.pt'},
        {'modelo': 'YOLOv5l', 'base_model': 'yolov5l.pt'},
        {'modelo': 'YOLOv8n', 'base_model': 'yolov8n.pt'},
        {'modelo': 'YOLOv8s', 'base_model': 'yolov8s.pt'},
        {'modelo': 'YOLOv8m', 'base_model': 'yolov8m.pt'},
        {'modelo': 'YOLOv8l', 'base_model': 'yolov8l.pt'},
        {'modelo': 'YOLOv11s', 'base_model': 'yolo11s.pt'},
        {'modelo': 'YOLOv11m', 'base_model': 'yolo11m.pt'},
        {'modelo': 'YOLOv11n', 'base_model': 'yolo11n.pt'},
        {'modelo': 'YOLOv11l', 'base_model': 'yolo11l.pt'},
       {'modelo': 'YOLOv11l', 'base_model': 'yolo11l.pt'},

    ],

    "LATENCY_WARMUPS": 10,
    "LATENCY_RUNS": 100,
}

RTDETR_CONFIG = {
                               
    "IMG_SIZE": 320,
    "NUM_EPOCHS": 10,
    "PATIENCE_EPOCHS": 100,
    "BATCH_SIZE": 8,
    "OPTIMIZER": "Adam",
    "LEARNING_RATE": 0.001,

    "DATASETS_TO_TRAIN": ['aquarium_pretrain','FishInvSplit','unificacaoDosOceanos'],

    "TRAINING_JOBS": [
        {'modelo': 'RT-DETR-L', 'base_model': 'rtdetr-l.pt'},
    ],

    "LATENCY_WARMUPS": 10,
    "LATENCY_RUNS": 100,
}