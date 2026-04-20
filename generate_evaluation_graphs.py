import matplotlib.pyplot as plt
import numpy as np

# Set professional style
plt.style.use('seaborn-v0_8-muted')
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 14,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.titlesize': 16,
    'grid.alpha': 0.3
})

def generate_metrics_chart():
    """Generates a bar chart for the five core evaluation metrics."""
    metrics = [
        'Schema\nValidity', 
        'Adjacency\nCompliance', 
        'Semantic\nAdherence', 
        'Latency\n< 5s', 
        'Area Error\n< 10%'
    ]
    values = [96, 88, 91, 84, 78]
    colors = ['#1a1a2e', '#16213e', '#0f3460', '#533483', '#e94560']

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(metrics, values, color=colors, width=0.6, edgecolor='white', linewidth=1.5)

    # Add background grid
    ax.yaxis.grid(True, linestyle='--', which='major', color='grey', alpha=.25)
    ax.set_axisbelow(True)

    # Label adjustments
    ax.set_ylim(0, 110)
    ax.set_ylabel('Pass Rate (%)', fontweight='bold')
    ax.set_title('VoxAssist Performance Metrics (N=50)', fontweight='bold', pad=20)

    # Add numeric labels on top of bars
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height}%',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha='center', va='bottom',
                    fontweight='bold',
                    color='#1a1a2e')

    plt.tight_layout()
    plt.savefig('metrics_chart.png', dpi=300, bbox_inches='tight')
    print("Saved metrics_chart.png")

def generate_comparison_radar():
    """Generates a radar chart comparing VoxAssist vs Baselines."""
    categories = ['Latency', 'Schema Compliance', 'Spatial Logic', 'Deployment Ease', 'Privacy']
    categories = [*categories, categories[0]]

    vox_assist = [92, 96, 91, 95, 100]
    gpt4o = [65, 98, 94, 70, 20]
    rule_base = [98, 100, 35, 10, 100]

    vox_assist = [*vox_assist, vox_assist[0]]
    gpt4o = [*gpt4o, gpt4o[0]]
    rule_base = [*rule_base, rule_base[0]]

    label_loc = np.linspace(start=0, stop=2 * np.pi, num=len(vox_assist))

    plt.figure(figsize=(8, 8))
    plt.subplot(polar=True)

    plt.plot(label_loc, vox_assist, label='VoxAssist (Ours)', color='#e94560', linewidth=3, marker='o')
    plt.fill(label_loc, vox_assist, color='#e94560', alpha=0.15)

    plt.plot(label_loc, gpt4o, label='GPT-4o (Cloud API)', color='#0f3460', linestyle='--', linewidth=2, marker='s')
    plt.fill(label_loc, gpt4o, color='#0f3460', alpha=0.05)

    plt.plot(label_loc, rule_base, label='Rule-Based (Legacy)', color='#555555', linestyle=':', linewidth=2, marker='^')
    
    plt.thetagrids(np.degrees(label_loc[:-1]), ['Latency', 'Schema', 'Spatial Logic', 'Deployability', 'Privacy'])
    
    plt.title('Architecture Capability Comparison', fontweight='bold', y=1.08)
    plt.legend(loc='lower center', bbox_to_anchor=(0.5, -0.2), ncol=3)
    
    plt.tight_layout()
    plt.savefig('comparison_chart.png', dpi=300, bbox_inches='tight')
    print("Saved comparison_chart.png")

if __name__ == "__main__":
    generate_metrics_chart()
    generate_comparison_radar()
