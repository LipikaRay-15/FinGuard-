import logging
from typing import Tuple
from database import DatabaseConnection
from exceptions import TransactionException, QueryExecutionException

class TransactionEngine:
    """
    Engine responsible for executing fraud risk evaluation logic on transactions.
    Interfaces with the database to run the multi-factor risk assessment stored procedure.
    """
    def __init__(self) -> None:
        self.db = DatabaseConnection()
        self.logger = logging.getLogger("finguard.engines.transaction_engine")

    def evaluate_transaction_risk(self, transaction_id: int) -> Tuple[int, str]:
        """
        Runs the `sp_assess_transaction_risk` stored procedure on MySQL
        to check blacklists/whitelists and execute active fraud rules.
        
        Args:
            transaction_id: The ID of the transaction to evaluate.
            
        Returns:
            A tuple of (risk_score, decision) where decision is 'APPROVED', 'DECLINED', or 'FLAGGED'.
            
        Raises:
            TransactionException: If there's an error running the evaluation or parsing results.
        """
        if not transaction_id or transaction_id <= 0:
            raise TransactionException(f"Invalid transaction ID for risk assessment: {transaction_id}")

        try:
            self.logger.info(f"Running risk assessment for transaction ID: {transaction_id}")
            
            # Setup session variables for OUT parameters
            self.db.execute("SET @p_risk_score = 0")
            self.db.execute("SET @p_decision = ''")
            
            # Execute Stored Procedure
            cursor = self.db.execute(
                "CALL sp_assess_transaction_risk(%s, @p_risk_score, @p_decision)",
                (transaction_id,)
            )
            cursor.close()
            
            # Retrieve OUT parameters
            result = self.db.fetch_one("SELECT @p_risk_score AS risk_score, @p_decision AS decision")
            
            if not result or result.get("decision") is None:
                raise TransactionException(
                    f"Stored procedure failed to return assessment results for transaction {transaction_id}."
                )
                
            risk_score = int(result["risk_score"])
            decision = str(result["decision"])
            
            # Check for error outputs from the stored procedure
            if decision == "ERROR_NO_TX":
                raise TransactionException(f"Stored procedure reported transaction {transaction_id} does not exist.")
                
            self.logger.info(
                f"Risk assessment complete for transaction ID {transaction_id}. "
                f"Score: {risk_score}, Decision: {decision}"
            )
            return risk_score, decision
            
        except QueryExecutionException as qee:
            self.logger.error(f"Database query failure assessing transaction {transaction_id}: {qee}", exc_info=True)
            raise TransactionException(f"Failed to assess transaction risk: {qee}")
        except Exception as e:
            self.logger.error(f"Unexpected error assessing transaction {transaction_id}: {e}", exc_info=True)
            raise TransactionException(f"Unexpected error in risk assessment: {e}")
