import pandas
import matplotlib.pyplot as plt


# fig_f1 = plt.Figure()
# fig_f2 = plt.Figure()

fig1, axes = plt.subplots(2, 1)
fig2, axes_rms = plt.subplots(1, 1)

rms_f1 = []
rms_f2 = []

for iteration in range(1, 50):
    cols = ["x1", "x2", "f1", "f2"]

    data = pandas.read_csv(
        f"finaldata{iteration}.dat",
        delim_whitespace=True,
        header=None,
        names=cols,
    )

    cols = ["x1", "x2", "f1truth", "f2truth"]

    data_truth = pandas.read_csv(
        f"finaldatatruth{iteration}.dat",
        delim_whitespace=True,
        header=None,
        names=cols,
    )

    merged = pandas.merge(data, data_truth, how="left", on=["x1", "x2"])

    # merged[["f1", "f1truth"]].plot.line(ax=axes[0])
    # merged[["f2", "f2truth"]].plot.line(ax=axes[1])

    axes[0].plot(abs(merged["f1"] - merged["f1truth"]), label=iteration)
    axes[1].plot(abs(merged["f2"] - merged["f2truth"]), label=iteration)

    rms_f1.append(((merged.f1 - merged.f1truth) ** 2).mean() ** .5)
    rms_f2.append(((merged.f2 - merged.f2truth) ** 2).mean() ** .5)
    # plt.scatter((data["f1"], data["f2"]), "o")

for ax in axes:
    # ax.set_ylim([0, 100])
    ax.set_yscale("log")
    ax.legend()
    # ax.get_legend().remove()

axes_rms.plot(rms_f1, label='f1')
axes_rms.plot(rms_f2, label='f2')

for ax in [axes_rms]:
    ax.set_yscale("log")
    ax.legend()
    ax.set_ylabel("RMS error")
    ax.set_xlabel("iteration")


plt.show()
