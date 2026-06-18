import logging
from typing import Any, Dict

from database import DatabaseConnection
from simulator.customer_generator import CustomerGenerator
from simulator.transaction_generator import TransactionGenerator

logger = logging.getLogger("finguard.simulator.fraud_simulator")


class FraudSimulator:
    """
    Main orchestrator class managing data simulation configs and performance reports.
    """
    def __init__(self) -> None:
        self.customer_gen = CustomerGenerator()
        self.tx_gen = TransactionGenerator()
        self.db = DatabaseConnection()

    def run_simulation(
        self, 
        num_customers: int = 5000, 
        num_transactions: int = 100000, 
        fraud_ratio: float = 0.05
    ) -> Dict[str, Any]:
        """
        Runs the simulation flow:
        1. Generates the synthetic customer pool.
        2. Streams transactions over day/night distributions.
        3. Compiles final execution metrics.
        """
        logger.info("=" * 60)
        logger.info(f"Starting FinGuard Fraud Simulation (C={num_customers}, T={num_transactions}, F={fraud_ratio})")
        logger.info("=" * 60)

        # 1. Generate Customers
        customers = self.customer_gen.generate_customers(num_customers)
        if not customers:
            logger.error("Failed to generate simulation customer pool.")
            return {}

        # 2. Generate and Process Transactions
        transactions = self.tx_gen.generate_transactions(
            customers=customers, 
            count=num_transactions, 
            fraud_ratio=fraud_ratio
        )

        # 3. Aggregate Simulation Metrics from the live database
        logger.info("Compiling simulator runtime statistics...")
        
        tx_stats = self.db.fetch_one(
            "SELECT "
            "  COUNT(*) as total, "
            "  SUM(CASE WHEN status = 'APPROVED' THEN 1 ELSE 0 END) as approved, "
            "  SUM(CASE WHEN status = 'DECLINED' THEN 1 ELSE 0 END) as declined, "
            "  SUM(CASE WHEN status = 'FLAGGED' THEN 1 ELSE 0 END) as flagged "
            "FROM transactions"
        )
        
        alert_stats = self.db.fetch_one("SELECT COUNT(*) as cnt FROM alerts")
        case_stats = self.db.fetch_one("SELECT COUNT(*) as cnt FROM cases")
        audit_stats = self.db.fetch_one("SELECT COUNT(*) as cnt FROM audit_logs")
        rule_stats = self.db.fetch_one("SELECT COUNT(*) as cnt FROM rule_execution_logs")

        summary = {
            "customers_generated": len(customers),
            "transactions_simulated": int(tx_stats["total"] or 0),
            "transactions_approved": int(tx_stats["approved"] or 0),
            "transactions_declined": int(tx_stats["declined"] or 0),
            "transactions_flagged": int(tx_stats["flagged"] or 0),
            "alerts_generated": int(alert_stats["cnt"] or 0),
            "cases_created": int(case_stats["cnt"] or 0),
            "audit_logs_recorded": int(audit_stats["cnt"] or 0),
            "rule_executions_logged": int(rule_stats["cnt"] or 0)
        }

        logger.info("=" * 60)
        logger.info("              SIMULATION RUN SUMMARY")
        logger.info("=" * 60)
        logger.info(f" Customers Generated:         {summary['customers_generated']}")
        logger.info(f" Transactions Simulated:      {summary['transactions_simulated']}")
        logger.info(f"   Approved:                  {summary['transactions_approved']}")
        logger.info(f"   Declined (Fraud Declines): {summary['transactions_declined']}")
        logger.info(f"   Flagged (Risk Alerts):     {summary['transactions_flagged']}")
        logger.info(f" Alerts Generated:            {summary['alerts_generated']}")
        logger.info(f" Cases Created:               {summary['cases_created']}")
        logger.info(f" Audit Logs Recorded:         {summary['audit_logs_recorded']}")
        logger.info(f" Rule Executions Logged:      {summary['rule_executions_logged']}")
        logger.info("=" * 60)

        return summary
