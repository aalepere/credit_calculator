import streamlit as st
import pandas as pd

# Constants
PERCENTAGE_BY_CREDIT_SCORE = {"A": 1, "B": 0.75, "C": 0.5, "D": 0.25, "E": 0.1}
MAX_LIMITS = {"A": 30000, "others": 20000}
TAEG = 0.15
PERIODIC_RATE = round((1 + TAEG) ** (30 / 365) - 1, 6)  # Calculate the periodic rate

class CreditCalculator:
    def __init__(self, taeg=TAEG, periodic_rate=PERIODIC_RATE):
        self.taeg = taeg
        self.periodic_rate = periodic_rate

    def compute_rate_factor(self, periods):
        """
        Compute the rate factor used in credit limit calculations.

        Parameters:
            periods (int): The number of periods for the calculation.

        Returns:
            float: The rate factor.
        """
        return (self.periodic_rate * (1 + self.periodic_rate) ** periods) / (
            (1 + self.periodic_rate) ** periods - 1
        )

    def compute_max_installment(self, credit_score, periods):
        """
        Compute the maximum installment based on the credit score.

        Parameters:
            credit_score (str): The credit score of the user (A, B, C, D, E).
            periods (int): The number of periods for the calculation.

        Returns:
            float: The maximum installment for the user.
        """
        if credit_score not in PERCENTAGE_BY_CREDIT_SCORE:
            raise ValueError("Invalid credit score")

        # Determine maximum limit based on credit score
        max_limit = MAX_LIMITS["A"] if credit_score == "A" else MAX_LIMITS["others"]
        percentage = PERCENTAGE_BY_CREDIT_SCORE[credit_score]
        rate_factor = self.compute_rate_factor(periods)

        return max_limit * percentage * rate_factor

    def compute_limit(self, credit_score, sum_inflow_6m, periods):
        """
        Compute the credit limit based on the user's inflow over the last 6 months.

        Parameters:
            credit_score (str): The credit score of the user (A, B, C, D, E).
            sum_inflow_6m (float): The total inflow over the last 6 months.
            periods (int): The number of periods for the calculation.

        Returns:
            float: The computed credit limit for the user.
        """
        # Calculate the monthly installment capacity as one-third of the average monthly inflow (i.e., 33% debt-to-income ratio)
        monthly_installment_capacity = round((sum_inflow_6m / 6) / 3, 2)

        # Calculate the final monthly installment, constrained by the maximum installment
        final_installment = round(min(
            monthly_installment_capacity,
            self.compute_max_installment(credit_score, periods),
        ), 2)

        # Calculate the credit limit capacity based on the final monthly installment
        credit_limit = round(
            (final_installment * (1 - (1 + self.periodic_rate) ** -periods))
            / self.periodic_rate,
            2
        )

        return credit_limit

    def compute_monthly_installments(self, amount, periods):
        """
        Compute the monthly installments for a given amount and period.

        Parameters:
            amount (float): The amount to be financed.
            periods (int): The number of periods for the calculation.

        Returns:
            tuple: Monthly installment amount and a DataFrame of the installment plan.
        """
        rate_factor = self.compute_rate_factor(periods)
        monthly_installment = round(rate_factor * amount, 2)

        # Define the columns for the installment DataFrame
        columns = [
            "Installment #",
            "Monthly Installment",
            "Interest",
            "Capital",
            "Remaining Capital",
        ]
        rows = []

        for i in range(1, periods + 1):
            interest = round(amount * self.periodic_rate, 2)
            capital = round(monthly_installment - interest, 2)
            remaining_capital = round(amount - capital, 2)
            rows.append(
                {
                    "Installment #": i,
                    "Monthly Installment": monthly_installment,
                    "Interest": interest,
                    "Capital": capital,
                    "Remaining Capital": max(0, remaining_capital),  # Ensure non-negative remaining capital
                }
            )
            amount = remaining_capital

        df = pd.DataFrame(rows, columns=columns)
        return monthly_installment, df

def main():
    st.title("Pay Later Credit Limit Calculator")

    # Initialize session state variables
    if 'credit_limit' not in st.session_state:
        st.session_state.credit_limit = None
    if 'dfs' not in st.session_state:
        st.session_state.dfs = []
    if 'monthly_repayment' not in st.session_state:
        st.session_state.monthly_repayment = None

    # Get user input for inflow and credit score
    inflow = st.number_input("Sum of client's inflows over the last 6 months:", min_value=0.0, step=0.01)
    credit_score = st.selectbox("Client's credit score:", list(PERCENTAGE_BY_CREDIT_SCORE.keys()))

    if st.button("Calculate Credit Limit"):
        calculator = CreditCalculator()
        st.session_state.credit_limit = calculator.compute_limit(credit_score, inflow, 3)
        st.success(f"Client's credit limit is {st.session_state.credit_limit}")

    if st.session_state.credit_limit is not None:
        # Handle financing process
        txn_amt = st.number_input("Enter the amount of the next financing:", min_value=0.0, step=0.01)
        number_payments = st.selectbox("Enter the number of repayments (3, 6 or 9):", [3, 6, 9])

        if txn_amt > st.session_state.credit_limit:
            st.error("Financing amount exceeds the limit. Please enter a valid amount.")
        elif st.button("Calculate Monthly Installments"):
            calculator = CreditCalculator()
            monthly_repayment, df = calculator.compute_monthly_installments(txn_amt, number_payments)
            st.session_state.monthly_repayment = monthly_repayment
            st.session_state.dfs.append(df)
            st.session_state.credit_limit = round(st.session_state.credit_limit - txn_amt, 2)
            st.success(f"{txn_amt} financed in {number_payments} times, for a monthly installment of {st.session_state.monthly_repayment}")

    if st.session_state.dfs:
        for i, df in enumerate(st.session_state.dfs):
            st.write(f"Financing plan {i + 1}")
            st.dataframe(df)
        st.write(f"Remaining credit limit: {st.session_state.credit_limit}")

if __name__ == "__main__":
    main()
