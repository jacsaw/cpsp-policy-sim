from shiny import App, ui, render
import matplotlib.pyplot as plt
import pandas as pd

def eitc_credit(income, phase_out_threshold, phase_in_rate, eitc_max, phase_out_rate):
    if income < phase_out_threshold:
        return min([income*phase_in_rate, eitc_max])
    else:
        po = (eitc_max - (income - phase_out_threshold)*phase_out_rate)
        if po > 0:
            return po
        else:
            return 0

# Define the UI
app_ui = ui.page_fluid(
    ui.h2("EITC Input Graphs"),
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_numeric("max_credit", "Maximum Credit:", value=1000, min=0, step=1),
            ui.input_numeric("phase_in_rate", "Phase-In Rate:", value=0.2, min=0, step=0.01),
            ui.input_numeric("phase_out_threshold", "Phase-Out Threshold:", value=40000, min=0, step=1000),
            ui.input_numeric("phase_out_rate", "Phase-Out Rate:", value=0.0765, min=0, step=0.01),
        ),
        ui.output_plot("plot")
    )
)

# Define the server logic
def server(input, output, session):
    @output
    @render.plot
    def plot():
        df = pd.DataFrame()

        # set income range over which to graph in increments of $500
        df["Income"] = range(0, 42000, 500)
        df["Eitc"] = df["Income"].apply(lambda x: eitc_credit(x, input.phase_out_threshold(), input.phase_in_rate(), input.max_credit(), input.phase_out_rate()))
        
        fig, ax = plt.subplots()
        ax.plot(df["Income"], df["Eitc"])
        ax.set_xlabel("Income")
        ax.set_ylabel("EITC")
        ax.set_title("EITC vs Income")
        return fig

# Create the Shiny app
app = App(app_ui, server)

# Run the app
if __name__ == "__main__":
    app.run()