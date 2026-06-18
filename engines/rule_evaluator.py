from abc import ABC, abstractmethod
from typing import Any
import logging

logger = logging.getLogger("finguard.engines.rule_evaluator")

class EvaluationStrategy(ABC):
    """
    Abstract Base Class representing a single operator evaluation strategy.
    """
    @abstractmethod
    def evaluate(self, value: Any, threshold: str) -> bool:
        """
        Evaluates the value against the threshold string.
        """
        pass

# Utility function to convert input values to float safely
def _to_num(x: Any) -> float:
    try:
        if isinstance(x, str):
            x = x.strip()
        return float(x)
    except (ValueError, TypeError):
        logger.warning(f"Could not convert value '{x}' of type {type(x)} to float. Defaulting to 0.0")
        return 0.0

class GreaterThanStrategy(EvaluationStrategy):
    def evaluate(self, value: Any, threshold: str) -> bool:
        return _to_num(value) > _to_num(threshold)

class LessThanStrategy(EvaluationStrategy):
    def evaluate(self, value: Any, threshold: str) -> bool:
        return _to_num(value) < _to_num(threshold)

class GreaterOrEqualStrategy(EvaluationStrategy):
    def evaluate(self, value: Any, threshold: str) -> bool:
        return _to_num(value) >= _to_num(threshold)

class LessOrEqualStrategy(EvaluationStrategy):
    def evaluate(self, value: Any, threshold: str) -> bool:
        return _to_num(value) <= _to_num(threshold)

class EqualsStrategy(EvaluationStrategy):
    def evaluate(self, value: Any, threshold: str) -> bool:
        # Perform comparison as normalized strings
        return str(value).strip().lower() == str(threshold).strip().lower()

class BetweenStrategy(EvaluationStrategy):
    def evaluate(self, value: Any, threshold: str) -> bool:
        # Expect threshold structure: "low,high" (e.g. "100.0,500.0")
        parts = threshold.split(",")
        if len(parts) == 2:
            low = _to_num(parts[0])
            high = _to_num(parts[1])
            val_num = _to_num(value)
            return low <= val_num <= high
        logger.error(f"Invalid threshold format for 'between' strategy: '{threshold}'")
        return False

class ContainsStrategy(EvaluationStrategy):
    def evaluate(self, value: Any, threshold: str) -> bool:
        return str(threshold).strip().lower() in str(value).lower()

class InStrategy(EvaluationStrategy):
    def evaluate(self, value: Any, threshold: str) -> bool:
        # Expect threshold structure: "item1,item2,item3"
        items = [i.strip().lower() for i in threshold.split(",")]
        return str(value).strip().lower() in items

class RuleEvaluator:
    """
    Registry context manager matching operators to concrete evaluation strategies.
    """
    _strategies = {
        ">": GreaterThanStrategy(),
        "<": LessThanStrategy(),
        ">=": GreaterOrEqualStrategy(),
        "<=": LessOrEqualStrategy(),
        "=": EqualsStrategy(),
        "between": BetweenStrategy(),
        "contains": ContainsStrategy(),
        "in": InStrategy(),
    }

    @classmethod
    def evaluate(cls, value: Any, operator: str, threshold: str) -> bool:
        op = operator.strip().lower()
        strategy = cls._strategies.get(op)
        if not strategy:
            raise ValueError(f"Evaluation failed: Unsupported operator '{operator}'")
        return strategy.evaluate(value, threshold)
