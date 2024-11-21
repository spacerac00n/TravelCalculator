import streamlit as st
import pandas as pd
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import base64
import io
import json
import os

class ExpenseTracker:
    def __init__(self, name):
        self.name = name
        self.friends = []
        self.expenses = []
        self.balances = {}
        self.bills = []

    def add_friend(self, name):
        capitalized_name = ' '.join(word.capitalize() for word in name.split())
        if capitalized_name not in self.friends:
            self.friends.append(capitalized_name)
            self.balances[capitalized_name] = {}

    def remove_friend(self, name):
        if name in self.friends:
            self.friends.remove(name)
            del self.balances[name]
            # Remove this friend from all split expenses
            for expense in self.expenses:
                if name in expense['splitAmong']:
                    expense['splitAmong'].remove(name)
            # Remove this friend from all bills
            for bill in self.bills:
                if name in bill['splitAmong']:
                    bill['splitAmong'].remove(name)

    def add_expense(self, paid_by, amount, description, split_among):
        expense = {
            'id': str(len(self.expenses) + 1),
            'paidBy': paid_by,
            'amount': float(amount),
            'description': description,
            'splitAmong': split_among,
            'date': datetime.now().isoformat()
        }
        self.expenses.append(expense)
        self.update_balances(expense)

    def update_balances(self, expense):
        per_person = expense['amount'] / len(expense['splitAmong'])
        for friend in expense['splitAmong']:
            if friend != expense['paidBy']:
                self.balances[expense['paidBy']][friend] = self.balances[expense['paidBy']].get(friend, 0) + per_person
                self.balances[friend][expense['paidBy']] = self.balances[friend].get(expense['paidBy'], 0) - per_person

    def cancel_expense(self, expense_id):
        expense = next((e for e in self.expenses if e['id'] == expense_id), None)
        if expense:
            per_person = expense['amount'] / len(expense['splitAmong'])
            for friend in expense['splitAmong']:
                if friend != expense['paidBy']:
                    self.balances[expense['paidBy']][friend] -= per_person
                    self.balances[friend][expense['paidBy']] += per_person
            self.expenses = [e for e in self.expenses if e['id'] != expense_id]

    def export_to_pdf(self):
        if 'calculators' not in st.session_state:
            load_data()
        tracker = st.session_state.calculators[st.session_state.current_calculator]
        

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        # Title
        elements.append(Paragraph(f"{tracker.name.upper()}", styles['Title']))
        elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%d/%m/%Y %H%MH')}", styles['Normal']))

        # Current Balances
        elements.append(Paragraph("Current Balances", styles['Heading2']))
        for friend, owes in self.balances.items():
            elements.append(Paragraph(friend, styles['Heading3']))
            for ower, amount in owes.items():
                if amount > 0:
                    elements.append(Paragraph(f"  {ower} owes {friend} ${amount:.2f}", styles['Normal']))

        # Expense History
        elements.append(Paragraph("Expense History", styles['Heading2']))
        expense_data = [['Date Added', 'Paid By', 'Amount', 'Description', 'Split Among']]
        for expense in self.expenses:
            expense_data.append([
                datetime.fromisoformat(expense['date']).strftime('%d/%m/%Y %H%MH'),
                expense['paidBy'],
                f"${expense['amount']:.2f}",
                expense['description'],
                ', '.join(expense['splitAmong'])
            ])

        table = Table(expense_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(table)

        doc.build(elements)
        buffer.seek(0)
        return buffer

def save_data():
    data = {
        'calculators': {name: calc.__dict__ for name, calc in st.session_state.calculators.items()},
        'current_calculator': st.session_state.current_calculator
    }
    with open('expense_tracker_data.json', 'w') as f:
        json.dump(data, f)

def load_data():
    if os.path.exists('expense_tracker_data.json'):
        with open('expense_tracker_data.json', 'r') as f:
            data = json.load(f)
        st.session_state.calculators = {name: ExpenseTracker(name) for name in data['calculators']}
        for name, calc_data in data['calculators'].items():
            st.session_state.calculators[name].__dict__.update(calc_data)
        st.session_state.current_calculator = data['current_calculator']
    else:
        st.session_state.calculators = {}
        st.session_state.current_calculator = None

def main():
    st.set_page_config(page_title="Expense Tracker", layout="wide")
    
    if 'calculators' not in st.session_state:
        load_data()

    

    # Page 1: Calculator List
    if st.session_state.current_calculator is None:

        # New section: User Instructions
        with st.expander("Grassjelly Calculator Instructions", expanded=True):
            st.markdown("""
            ### Grassjelly Guide 

            1. **Create a Calculator:**
               - Enter your trip names
               - Create New Calculator = Create a trip

            2. **Manage Your Calculator:**
               - Click "Open" to access an existing calculator
               - Use "Delete" to remove a calculator you no longer need

            3. **Inside a Calculator:**
               - Add friends 
               - Enter bills, who paid and how to split
               - Current Balance: See who owes who
               - Check the expense history
               - Cancel incorrect entries
               - Export a PDF report 

            4. **NO-GO CRITERIA:**
               - Removing friends can only be done at the **START**
               - Do not attempt to remove friends after submission of bills
            """)
        st.header("My Calculators")
        for calc_name in list(st.session_state.calculators.keys()):  # Use list() to avoid runtime modification issues
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                if st.button(f"Open {calc_name}"):
                    st.session_state.current_calculator = calc_name
                    st.rerun()
            with col2:
                if st.button(f"Delete {calc_name}"):
                    st.session_state.calculator_to_delete = calc_name
                    st.rerun()
            
        if 'calculator_to_delete' in st.session_state:
            calc_name = st.session_state.calculator_to_delete
            st.warning(f"Are you sure you want to delete {calc_name}?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Yes, delete"):
                    del st.session_state.calculators[calc_name]
                    del st.session_state.calculator_to_delete
                    save_data()
                    st.success(f"{calc_name} has been deleted.")
                    st.rerun()
            with col2:
                if st.button("No, cancel"):
                    del st.session_state.calculator_to_delete
                    st.rerun()
        
        st.subheader("Create New Calculator")
        new_calc_name = st.text_input("Enter calculator name")
        if st.button("Create"):
            if new_calc_name and new_calc_name not in st.session_state.calculators:
                st.session_state.calculators[new_calc_name] = ExpenseTracker(new_calc_name)
                st.session_state.current_calculator = new_calc_name
                save_data()
                st.rerun()
            elif new_calc_name in st.session_state.calculators:
                st.error("A calculator with this name already exists.")
    
    # Page 2: Expense Tracker
    else:
        tracker = st.session_state.calculators[st.session_state.current_calculator]
        st.title(f"{tracker.name}".upper())

        if st.button("Back to Calculator List"):
            st.session_state.current_calculator = None
            save_data()
            st.rerun()

        # Add Friend Section
        with st.container():
            
            col1, col2 = st.columns(2)
            with col1:
                new_friend = st.text_input("Enter friend's name")
                if st.button("Add Friend"):
                    if new_friend:
                        tracker.add_friend(new_friend)
                        st.success(f"Added {new_friend} to the group!")
                        save_data()
                        st.rerun()
            with col2:
                friend_to_remove = st.selectbox("Select friend to remove", tracker.friends)
                if st.button("Remove Friend"):
                    if friend_to_remove:
                        tracker.remove_friend(friend_to_remove)
                        st.success(f"Removed {friend_to_remove} from the group!")
                        save_data()
                        st.rerun()

        # Add Bills Section
        with st.container():
            st.subheader("Add Bills")
            with st.form("add_bill_form"):
                description = st.text_input("Description")
                amount = st.text_input("Amount")
                paid_by = st.selectbox("Paid By", tracker.friends)
                split_among = st.multiselect("Split Among", tracker.friends)
                submitted = st.form_submit_button("Add Bill")
                if submitted:
                    try:
                        amount_float = float(amount)
                        if description and amount_float > 0 and paid_by and split_among:
                            tracker.bills.append({
                                "description": description,
                                "amount": amount_float,
                                "paidBy": paid_by,
                                "splitAmong": split_among
                            })
                            st.success("Bill added successfully!")
                            save_data()
                            st.rerun()
                        else:
                            st.error("Please fill in all fields correctly.")
                    except ValueError:
                        st.error("Please enter a valid number for the amount.")

        # Display and manage bills
        # Display and manage bills
        # Display and manage bills
        # Display and manage bills
        if tracker.bills:
            with st.container():
                st.subheader("Current Bills")
                df = pd.DataFrame(tracker.bills)
                df['amount'] = df['amount'].apply(lambda x: f"${x:.2f}")
                df['splitAmong'] = df['splitAmong'].apply(lambda x: ', '.join(x))
                df.columns = ['Description', 'Amount', 'Paid By', 'Split Among']  # Rename columns
                
                # Apply styling without additional formatting for Amount
                styled_df = df.style.set_properties(**{'font-weight': 'bold'}, subset=['Description', 'Amount', 'Paid By', 'Split Among'])
                
                # Convert to HTML and remove the index column using CSS
                html = styled_df.to_html(index=False)  # Exclude index directly in to_html method
                html = html.replace('<table', '<table style="border-collapse: collapse; width: 100%;"')
                html = html.replace('<th>', '<th style="border: 1px solid #ddd; padding: 8px; background-color: #f2f2f2;">')
                html = html.replace('<td>', '<td style="border: 1px solid #ddd; padding: 8px;">')
                
                st.markdown(html, unsafe_allow_html=True)

                if st.button("Submit All Bills"):
                    for bill in tracker.bills:
                        tracker.add_expense(bill["paidBy"], bill["amount"], bill["description"], bill["splitAmong"])
                    tracker.bills = []
                    st.success("All bills submitted successfully!")
                    save_data()
                    st.rerun()

        # Expense History
        with st.container():
            st.subheader("Expense History")
            for expense in tracker.expenses:
                with st.expander(f"{expense['description']} - ${expense['amount']:.2f}"):
                    st.write(f"Paid by: {expense['paidBy']}")
                    st.write(f"Split among: {', '.join(expense['splitAmong'])}")
                    st.write(f"Date: {datetime.fromisoformat(expense['date']).strftime('%d/%m/%Y %H%MH')}")
                    if st.button("Cancel Expense", key=f"cancel_{expense['id']}"):
                        tracker.cancel_expense(expense['id'])
                        st.success("Expense cancelled successfully!")
                        save_data()
                        st.rerun()

        # Current Balances
        with st.container():
            st.subheader("Current Balances")
            balance_html = "<div style='border: 2px solid #ddd; padding: 10px; border-radius: 5px;'>"
            for friend, owes in tracker.balances.items():
                balance_html += f"<h3>{friend}</h3>"
                for ower, amount in owes.items():
                    if amount > 0:
                        balance_html += f"<p>{ower} owes {friend} ${amount:.2f}</p>"
            balance_html += "</div>"
            st.markdown(balance_html, unsafe_allow_html=True)

        # Export to PDF
        if st.button("Export to PDF"):
            pdf_buffer = tracker.export_to_pdf()
            b64 = base64.b64encode(pdf_buffer.getvalue()).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="expense_tracker_report_{tracker.name}.pdf">Download PDF Report</a>'
            st.markdown(href, unsafe_allow_html=True)

if __name__ == "__main__":
    main()