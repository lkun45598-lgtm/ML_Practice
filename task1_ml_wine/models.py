# -*- coding: utf-8 -*-
"""四个传统分类模型的定义与超参数搜索空间（供主流程与跨数据集对照复用）。"""
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression


def build_models():
    """返回 {模型名: (estimator, 参数网格)}；参数键用 clf__ 前缀以配合 Pipeline。"""
    return {
        "SVM": (
            SVC(class_weight="balanced", probability=True, random_state=42),
            {"clf__C": [1, 10], "clf__gamma": ["scale", 0.1], "clf__kernel": ["rbf"]},
        ),
        "决策树": (
            DecisionTreeClassifier(class_weight="balanced", random_state=42),
            {"clf__max_depth": [None, 10, 20], "clf__min_samples_leaf": [1, 5]},
        ),
        "随机森林": (
            RandomForestClassifier(class_weight="balanced", random_state=42, n_jobs=-1),
            {"clf__n_estimators": [200, 400], "clf__max_depth": [None, 20]},
        ),
        "逻辑回归": (
            LogisticRegression(class_weight="balanced", max_iter=2000),
            {"clf__C": [0.5, 1, 10]},
        ),
    }
