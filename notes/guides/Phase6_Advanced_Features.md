# Phase 6: Advanced Features
## Week 6+ - Taking It to the Next Level

### Overview
**Goal:** Add advanced features that make the optimizer truly powerful and differentiate it from simple build planners. These features leverage the solid foundation from Phases 1-5 to provide insights and capabilities not available elsewhere.

**Time Estimate:** Ongoing (pick and choose features)
**Priority:** Optional - Core functionality complete, these are enhancements

**Feature Categories:**
1. Multi-Objective Optimization (Pareto frontier)
2. Budget Progression Analysis
3. League Mechanic Integration
4. ML-Powered Recommendations
5. Web Interface
6. Community Features

---

## Prerequisites

### Completed
- ✅ Phase 1-5: Full working optimizer

### New Libraries (as needed)
```bash
# ML features
pip install scikit-learn pandas

# Web interface
pip install fastapi uvicorn

# Visualization
pip install plotly seaborn

# Database (for web version)
pip install sqlalchemy redis
```

---

## Feature 1: Pareto Frontier Optimization

### Overview
Instead of finding one "best" build, find the Pareto frontier - a set of builds where no build is strictly better in all objectives. This lets users choose their preferred trade-off between DPS, EHP, and cost.

### Implementation

**Claude Code Prompt:**
> "Create src/optimizer/pareto.py implementing multi-objective optimization:
>
> ```python
> from deap import tools
> import numpy as np
>
> class ParetoOptimizer:
>     '''Multi-objective Pareto frontier optimization.'''
>
>     def __init__(self, calculator, data_loader, constraints):
>         self.calculator = calculator
>         self.data = data_loader
>         self.constraints = constraints
>
>     def find_pareto_frontier(
>         self,
>         seed_build: Build,
>         objectives: List[str] = ['dps', 'ehp', 'cost'],
>         population_size: int = 100,
>         generations: int = 150
>     ) -> List[Build]:
>         '''
>         Find Pareto-optimal builds.
>
>         Uses NSGA-II algorithm (Non-dominated Sorting Genetic Algorithm).
>
>         Returns:
>             List of Pareto-optimal builds
>         '''
>
>         # Setup NSGA-II
>         creator.create('FitnessMulti', base.Fitness,
>                        weights=(1.0, 1.0, -1.0))  # max DPS, max EHP, min cost
>         creator.create('Individual', list, fitness=creator.FitnessMulti)
>
>         toolbox = base.Toolbox()
>         toolbox.register('individual', self.create_random_individual, seed_build)
>         toolbox.register('population', tools.initRepeat, list, toolbox.individual)
>         toolbox.register('evaluate', self.evaluate_multiobjective)
>         toolbox.register('mate', self.crossover)
>         toolbox.register('mutate', self.mutate)
>         toolbox.register('select', tools.selNSGA2)
>
>         # Initialize population
>         population = toolbox.population(n=population_size)
>
>         # Evaluate
>         fitnesses = map(toolbox.evaluate, population)
>         for ind, fit in zip(population, fitnesses):
>             ind.fitness.values = fit
>
>         # Evolution
>         for gen in range(generations):
>             # Select
>             offspring = toolbox.select(population, len(population))
>             offspring = list(map(toolbox.clone, offspring))
>
>             # Crossover and mutation
>             for child1, child2 in zip(offspring[::2], offspring[1::2]):
>                 if random.random() < 0.7:
>                     toolbox.mate(child1, child2)
>                     del child1.fitness.values
>                     del child2.fitness.values
>
>             for mutant in offspring:
>                 if random.random() < 0.2:
>                     toolbox.mutate(mutant)
>                     del mutant.fitness.values
>
>             # Evaluate invalid individuals
>             invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
>             fitnesses = map(toolbox.evaluate, invalid_ind)
>             for ind, fit in zip(invalid_ind, fitnesses):
>                 ind.fitness.values = fit
>
>             # Replace population
>             population = toolbox.select(population + offspring, population_size)
>
>             # Progress
>             if gen % 10 == 0:
>                 print(f'Generation {gen}: {len(population)} individuals')
>
>         # Extract Pareto front
>         pareto_front = tools.sortNondominated(population, len(population),
>                                                first_front_only=True)[0]
>
>         # Convert to Build objects
>         pareto_builds = [self.individual_to_build(ind) for ind in pareto_front]
>
>         return pareto_builds
>
>     def evaluate_multiobjective(self, individual) -> Tuple[float, float, float]:
>         '''
>         Evaluate multiple objectives.
>
>         Returns:
>             (dps, ehp, -cost): Tuple of objective values
>         '''
>         build = self.individual_to_build(individual)
>
>         try:
>             stats = build.evaluate(self.calculator)
>             dps = stats['dps']
>             ehp = stats['ehp']
>             cost = self.calculate_build_cost(build)
>
>             return (dps, ehp, -cost)  # Negative cost (minimize)
>         except:
>             return (0, 0, -999999999)  # Invalid build
>
>     def visualize_pareto_frontier(self, pareto_builds, output='pareto.html'):
>         '''Create interactive 3D plot of Pareto frontier.'''
>         import plotly.graph_objects as go
>
>         dps_vals = [b.stats['dps'] for b in pareto_builds]
>         ehp_vals = [b.stats['ehp'] for b in pareto_builds]
>         cost_vals = [self.calculate_build_cost(b) for b in pareto_builds]
>
>         fig = go.Figure(data=[go.Scatter3d(
>             x=dps_vals,
>             y=ehp_vals,
>             z=cost_vals,
>             mode='markers',
>             marker=dict(
>                 size=8,
>                 color=dps_vals,
>                 colorscale='Viridis',
>                 showscale=True
>             ),
>             text=[f'Build {i}' for i in range(len(pareto_builds))],
>             hovertemplate='<b>%{text}</b><br>' +
>                          'DPS: %{x:,.0f}<br>' +
>                          'EHP: %{y:,.0f}<br>' +
>                          'Cost: %{z:,.0f} chaos<br>'
>         )])
>
>         fig.update_layout(
>             title='Pareto Frontier: DPS vs EHP vs Cost',
>             scene=dict(
>                 xaxis_title='DPS',
>                 yaxis_title='EHP',
>                 zaxis_title='Cost (chaos)'
>             )
>         )
>
>         fig.write_html(output)
>         print(f'✓ Pareto frontier saved to {output}')
> ```
>
> This provides users with a range of optimal builds to choose from."

---

## Feature 2: Budget Progression Analysis

### Overview
Show how builds improve as budget increases, identifying the best upgrade order.

### Implementation

**Claude Code Prompt:**
> "Create src/analyzer/budget_progression.py:
>
> ```python
> class BudgetProgressionAnalyzer:
>     '''Analyze build performance across budget levels.'''
>
>     def analyze_progression(
>         self,
>         skill: str,
>         class_name: str,
>         ascendancy: str,
>         budget_steps: List[int] = [100000, 500000, 1000000, 5000000, 10000000, 50000000]
>     ) -> pd.DataFrame:
>         '''
>         Optimize builds at multiple budget levels.
>
>         Args:
>             skill: Main skill
>             class_name: Character class
>             ascendancy: Ascendancy
>             budget_steps: List of budget levels in chaos
>
>         Returns:
>             DataFrame with budget, dps, ehp, life for each level
>         '''
>
>         results = []
>
>         for budget in budget_steps:
>             console.print(f'Optimizing at {budget:,} chaos...')
>
>             # Create seed
>             seed = Build(
>                 class_name=class_name,
>                 ascendancy=ascendancy,
>                 main_skill=skill
>             )
>
>             # Optimize
>             constraints = Constraints(max_budget_chaos=budget)
>             optimizer = MasterOptimizer(calc, data, constraints)
>             best = optimizer.optimize_balanced(seed)
>
>             # Record results
>             results.append({
>                 'budget_chaos': budget,
>                 'budget_div': budget / 100000,
>                 'dps': best.stats['dps'],
>                 'ehp': best.stats['ehp'],
>                 'life': best.stats['life'],
>                 'fire_res': best.stats['fireRes'],
>                 'cold_res': best.stats['coldRes'],
>                 'lightning_res': best.stats['lightningRes'],
>             })
>
>         return pd.DataFrame(results)
>
>     def identify_key_upgrades(
>         self,
>         progression_df: pd.DataFrame
>     ) -> List[Dict]:
>         '''
>         Identify budget points with biggest performance jumps.
>
>         Returns:
>             List of key upgrade points with analysis
>         '''
>         key_upgrades = []
>
>         for i in range(1, len(progression_df)):
>             prev = progression_df.iloc[i-1]
>             curr = progression_df.iloc[i]
>
>             dps_gain = curr['dps'] - prev['dps']
>             dps_gain_pct = (dps_gain / prev['dps']) * 100
>             budget_increase = curr['budget_chaos'] - prev['budget_chaos']
>             efficiency = dps_gain / budget_increase
>
>             if dps_gain_pct > 20:  # Significant jump
>                 key_upgrades.append({
>                     'from_budget': prev['budget_div'],
>                     'to_budget': curr['budget_div'],
>                     'dps_gain': dps_gain,
>                     'dps_gain_pct': dps_gain_pct,
>                     'efficiency': efficiency,
>                     'analysis': f'{dps_gain_pct:.1f}% DPS increase for '
>                                f'{budget_increase:,} chaos investment'
>                 })
>
>         return key_upgrades
>
>     def plot_progression(self, progression_df: pd.DataFrame, output='progression.html'):
>         '''Create interactive progression charts.'''
>         import plotly.graph_objects as go
>         from plotly.subplots import make_subplots
>
>         fig = make_subplots(
>             rows=2, cols=1,
>             subplot_titles=('DPS vs Budget', 'EHP vs Budget')
>         )
>
>         # DPS plot
>         fig.add_trace(
>             go.Scatter(
>                 x=progression_df['budget_div'],
>                 y=progression_df['dps'],
>                 mode='lines+markers',
>                 name='DPS',
>                 line=dict(color='red', width=3)
>             ),
>             row=1, col=1
>         )
>
>         # EHP plot
>         fig.add_trace(
>             go.Scatter(
>                 x=progression_df['budget_div'],
>                 y=progression_df['ehp'],
>                 mode='lines+markers',
>                 name='EHP',
>                 line=dict(color='blue', width=3)
>             ),
>             row=2, col=1
>         )
>
>         fig.update_xaxes(title_text='Budget (divines)', row=2, col=1)
>         fig.update_yaxes(title_text='DPS', row=1, col=1)
>         fig.update_yaxes(title_text='EHP', row=2, col=1)
>
>         fig.update_layout(height=800, title_text='Build Progression Analysis')
>         fig.write_html(output)
>
>     def generate_upgrade_plan(
>         self,
>         current_build: Build,
>         target_budget: int
>     ) -> List[str]:
>         '''
>         Generate step-by-step upgrade recommendations.
>
>         Returns:
>             List of upgrade steps with priorities
>         '''
>         # Analyze current build
>         current_cost = self.calculate_build_cost(current_build)
>         available_budget = target_budget - current_cost
>
>         # Test upgrading each slot
>         upgrades = []
>         for slot in current_build.items.keys():
>             # Find better items for this slot
>             better_items = self.find_upgrades_for_slot(
>                 current_build,
>                 slot,
>                 available_budget
>             )
>
>             for item_name, item_price in better_items:
>                 # Test upgrade
>                 test_build = current_build.clone()
>                 test_build.items[slot] = item_name
>                 stats = test_build.evaluate(self.calculator)
>
>                 dps_gain = stats['dps'] - current_build.stats['dps']
>                 value = dps_gain / item_price  # Value per chaos
>
>                 upgrades.append({
>                     'slot': slot,
>                     'item': item_name,
>                     'cost': item_price,
>                     'dps_gain': dps_gain,
>                     'value': value
>                 })
>
>         # Sort by value
>         upgrades.sort(key=lambda x: x['value'], reverse=True)
>
>         # Generate plan
>         plan = []
>         remaining = available_budget
>         for upgrade in upgrades:
>             if upgrade['cost'] <= remaining:
>                 plan.append(
>                     f\"{upgrade['slot']}: {upgrade['item']} \"
>                     f\"({upgrade['cost']:,} chaos, +{upgrade['dps_gain']:,.0f} DPS)\"
>                 )
>                 remaining -= upgrade['cost']
>
>         return plan
> ```"

---

## Feature 3: League Mechanic Integration

### Overview
Optimize builds for specific league mechanics (delve, breach, expedition, etc.)

### Implementation

**Claude Code Prompt:**
> "Create src/analyzer/league_mechanics.py:
>
> ```python
> class LeagueMechanicOptimizer:
>     '''Optimize builds for specific league mechanics.'''
>
>     MECHANIC_REQUIREMENTS = {
>         'Delve': {
>             'min_chaos_res': -40,  # Darkness resistance important
>             'min_life': 5000,      # One-shots common
>             'preferred_defensive': 'armour',
>             'weight_dps': 0.4,
>             'weight_ehp': 0.6,     # Survival critical
>         },
>         'Breach': {
>             'min_clear_speed': True,  # Need good clear
>             'min_aoe': 'medium',
>             'weight_dps': 0.7,
>             'weight_ehp': 0.3,
>         },
>         'Bossing': {
>             'min_single_target_dps': 5_000_000,
>             'min_ehp': 300_000,
>             'required_mechanics': ['boss_damage'],
>             'weight_dps': 0.8,
>             'weight_ehp': 0.2,
>         },
>         'Mapping': {
>             'min_movement_speed': 20,
>             'min_clear_speed': True,
>             'weight_dps': 0.5,
>             'weight_ehp': 0.3,
>             'weight_speed': 0.2,
>         }
>     }
>
>     def optimize_for_mechanic(
>         self,
>         seed_build: Build,
>         mechanic: str,
>         budget: int
>     ) -> Build:
>         '''Optimize build for specific content type.'''
>
>         requirements = self.MECHANIC_REQUIREMENTS.get(mechanic, {})
>
>         # Create specialized constraints
>         constraints = Constraints(
>             max_budget_chaos=budget,
>             **{k: v for k, v in requirements.items()
>                if k.startswith('min_')}
>         )
>
>         # Create specialized fitness function
>         def mechanic_fitness(stats: dict) -> float:
>             dps = stats.get('dps', 0) / 10_000_000
>             ehp = stats.get('ehp', 0) / 500_000
>             speed = stats.get('movement_speed', 0) / 100
>
>             weights = requirements
>             fitness = (
>                 dps * weights.get('weight_dps', 0.5) +
>                 ehp * weights.get('weight_ehp', 0.3) +
>                 speed * weights.get('weight_speed', 0.2)
>             )
>
>             return fitness
>
>         # Optimize with custom fitness
>         optimizer = MasterOptimizer(calc, data, constraints)
>         optimizer.fitness_function = mechanic_fitness
>         best = optimizer.optimize_balanced(seed_build)
>
>         return best
> ```"

---

## Feature 4: ML-Powered Recommendations

### Overview
Use machine learning to learn from successful builds and recommend synergies.

### Implementation

**Claude Code Prompt:**
> "Create src/ml/build_recommender.py:
>
> ```python
> from sklearn.ensemble import RandomForestClassifier
> from sklearn.feature_extraction import DictVectorizer
> import pandas as pd
>
> class BuildRecommender:
>     '''ML-powered build recommendations.'''
>
>     def __init__(self):
>         self.model = RandomForestClassifier(n_estimators=100)
>         self.vectorizer = DictVectorizer()
>         self.trained = False
>
>     def train_from_poe_ninja(self, league='Standard'):
>         '''
>         Train on successful builds from poe.ninja.
>
>         Learns:
>         - Which items work well together
>         - Which keystones are taken together
>         - Which support gems are used for each skill
>         '''
>
>         # Fetch top builds
>         builds = self.fetch_top_builds(league, limit=1000)
>
>         # Extract features
>         X = []
>         y = []
>
>         for build in builds:
>             features = self.extract_features(build)
>             X.append(features)
>
>             # Label: is this a high-performing build?
>             is_good = (
>                 build['dps'] > 5_000_000 and
>                 build['life'] > 4500 and
>                 build['all_res_capped']
>             )
>             y.append(1 if is_good else 0)
>
>         # Vectorize and train
>         X_vec = self.vectorizer.fit_transform(X)
>         self.model.fit(X_vec, y)
>         self.trained = True
>
>         print(f'✓ Trained on {len(builds)} builds')
>
>     def extract_features(self, build: dict) -> dict:
>         '''Extract ML features from build.'''
>         features = {
>             'skill': build['main_skill'],
>             'class': build['class_name'],
>             'ascendancy': build['ascendancy'],
>             'level': build['level'],
>             # Item types
>             'weapon_type': build.get('weapon_base', 'unknown'),
>             'body_armour_type': build.get('body_base', 'unknown'),
>             # Key keystones
>             **{f'has_{ks}': ks in build.get('keystones', [])
>                for ks in ['Resolute Technique', 'Point Blank', 'Acrobatics']},
>             # Support gems
>             **{f'uses_{gem}': gem in build.get('support_gems', [])
>                for gem in ['Melee Physical Damage', 'Brutality', 'Impale']},
>         }
>         return features
>
>     def recommend_items(self, current_build: Build, slot: str) -> List[str]:
>         '''Recommend items that work well with current build.'''
>
>         if not self.trained:
>             raise ValueError('Model not trained')
>
>         # Get current build features
>         base_features = self.extract_features_from_build(current_build)
>
>         # Test each available item
>         items = self.data.items.get_items_for_slot(slot)
>         scores = {}
>
>         for item_name in items:
>             # Create features with this item
>             features = base_features.copy()
>             features[f'item_{slot}'] = item_name
>
>             # Predict
>             X = self.vectorizer.transform([features])
>             prob = self.model.predict_proba(X)[0][1]  # Probability of being good build
>
>             scores[item_name] = prob
>
>         # Sort by score
>         recommendations = sorted(scores.items(), key=lambda x: x[1], reverse=True)
>         return [item for item, score in recommendations[:10]]
>
>     def recommend_keystones(self, current_build: Build) -> List[str]:
>         '''Recommend keystones that would improve the build.'''
>         # Similar to recommend_items, but for passive keystones
>         pass
> ```"

---

## Feature 5: Web Interface

### Overview
Create a web UI for easier access and sharing.

### Implementation

**Claude Code Prompt:**
> "Create a FastAPI web service in src/web/app.py:
>
> ```python
> from fastapi import FastAPI, BackgroundTasks
> from fastapi.responses import HTMLResponse
> from pydantic import BaseModel
> import uvicorn
> from typing import Optional
> import uuid
>
> app = FastAPI(title='PoE Build Optimizer')
>
> # In-memory job storage (use Redis in production)
> jobs = {}
>
> class OptimizationRequest(BaseModel):
>     skill: str
>     class_name: str = 'Duelist'
>     ascendancy: str = 'Slayer'
>     budget: int = 5_000_000
>     min_life: int = 4000
>     min_dps: int = 1_000_000
>     strategy: str = 'balanced'
>
> class OptimizationResult(BaseModel):
>     job_id: str
>     status: str  # pending, running, completed, failed
>     progress: int  # 0-100
>     result: Optional[dict] = None
>     error: Optional[str] = None
>
> @app.get('/')
> async def root():
>     '''Landing page'''
>     return HTMLResponse('''
>     <html>
>       <head><title>PoE Build Optimizer</title></head>
>       <body>
>         <h1>Path of Exile Build Optimizer</h1>
>         <p>API documentation: <a href=\"/docs\">/docs</a></p>
>       </body>
>     </html>
>     ''')
>
> @app.post('/optimize', response_model=OptimizationResult)
> async def optimize_build(
>     request: OptimizationRequest,
>     background_tasks: BackgroundTasks
> ):
>     '''Start build optimization'''
>
>     # Generate job ID
>     job_id = str(uuid.uuid4())
>
>     # Create job
>     jobs[job_id] = {
>         'status': 'pending',
>         'progress': 0,
>         'result': None,
>         'error': None
>     }
>
>     # Start optimization in background
>     background_tasks.add_task(
>         run_optimization,
>         job_id,
>         request
>     )
>
>     return OptimizationResult(
>         job_id=job_id,
>         status='pending',
>         progress=0
>     )
>
> @app.get('/status/{job_id}', response_model=OptimizationResult)
> async def get_status(job_id: str):
>     '''Get optimization status'''
>
>     job = jobs.get(job_id)
>     if not job:
>         return {'error': 'Job not found'}
>
>     return OptimizationResult(
>         job_id=job_id,
>         status=job['status'],
>         progress=job['progress'],
>         result=job['result'],
>         error=job['error']
>     )
>
> async def run_optimization(job_id: str, request: OptimizationRequest):
>     '''Background task to run optimization'''
>
>     try:
>         jobs[job_id]['status'] = 'running'
>
>         # Create seed build
>         seed = Build(
>             class_name=request.class_name,
>             ascendancy=request.ascendancy,
>             main_skill=request.skill
>         )
>
>         # Create constraints
>         constraints = Constraints(
>             min_life=request.min_life,
>             min_dps=request.min_dps,
>             max_budget_chaos=request.budget
>         )
>
>         # Progress callback
>         def update_progress(progress: int):
>             jobs[job_id]['progress'] = progress
>
>         # Optimize
>         optimizer = MasterOptimizer(calc, data, constraints)
>         optimizer.progress_callback = update_progress
>         best = optimizer.optimize_balanced(seed)
>
>         # Generate result
>         generator = BuildXMLGenerator(data.items, data.gems)
>         xml = generator.generate_xml(best)
>         code = generator.encode_for_import(xml)
>
>         # Store result
>         jobs[job_id]['status'] = 'completed'
>         jobs[job_id]['progress'] = 100
>         jobs[job_id]['result'] = {
>             'pob_code': code,
>             'stats': best.stats,
>             'items': {slot: item for slot, item in best.items.items()},
>             'passive_nodes': list(best.allocated_nodes)
>         }
>
>     except Exception as e:
>         jobs[job_id]['status'] = 'failed'
>         jobs[job_id]['error'] = str(e)
>
> if __name__ == '__main__':
>     uvicorn.run(app, host='0.0.0.0', port=8000)
> ```
>
> Add frontend with React or Vue for full web interface."

---

## Feature 6: Community Integration

### Overview
Features that connect with the PoE community.

### Ideas

1. **Discord Bot**
   ```python
   # Bot that responds to !optimize commands
   # Queues optimization requests
   # DMs results when complete
   ```

2. **Build Sharing**
   ```python
   # Share optimized builds with unique URLs
   # Rate and comment on builds
   # Browse popular builds
   ```

3. **Competition Mode**
   ```python
   # Weekly challenges: best build under X budget
   # Leaderboards
   # Community voting
   ```

4. **PoB Integration PR**
   ```python
   # Contribute optimizer back to PoB as a feature
   # Port to Lua
   # Add UI in PoB
   ```

---

## Implementation Priority

### High Priority (Do First)
1. ✅ Pareto frontier optimization - Provides real user value
2. ✅ Budget progression analysis - Very useful for planning
3. ⭐ Enhanced visualization - Makes results understandable

### Medium Priority
4. League mechanic optimization - Nice for specialized content
5. ML recommendations - Interesting but requires training data
6. Web interface - Broader audience but more maintenance

### Low Priority (Nice to Have)
7. Discord bot - Community feature
8. Build sharing - Requires infrastructure
9. Competition mode - Fun but not essential

---

## Testing Strategy

Each advanced feature needs:
- Unit tests for core logic
- Integration tests with full pipeline
- Performance tests (shouldn't slow down optimizer)
- User acceptance tests (is it actually useful?)

---

## Documentation

For each feature, document:
- What it does and why it's useful
- How to use it (CLI commands, API endpoints)
- Examples with screenshots/plots
- Limitations and caveats

---

## Success Metrics

Track:
- **Usage:** Which features are actually used?
- **Performance:** Do they slow down optimization?
- **Accuracy:** Do ML recommendations help?
- **User Feedback:** What do users want most?

---

## Deployment Considerations

### For Web Interface
- Use Redis for job queue (not in-memory dict)
- Add rate limiting (prevent spam)
- Add authentication (API keys)
- Deploy on cloud (Heroku, AWS, etc.)
- Monitor with logging/metrics

### For ML Features
- Pre-train models, don't train on startup
- Update models periodically (new league data)
- Cache predictions
- Fallback to heuristics if model unavailable

---

## Long-Term Vision

**Year 1:** Core optimizer stable and widely used

**Year 2:** Advanced features (ML, web interface)

**Year 3:** Contribute back to PoB, integrated optimizer in official app

**Community Impact:**
- Lower barrier to entry (good builds without expertise)
- Better understanding of build mechanics
- More build diversity (discover non-meta builds)

---

## Quick Start Commands

```bash
# Pareto frontier
python -m src.cli pareto --skill Cyclone --count 20

# Budget progression
python -m src.cli budget-progression --skill Cyclone --budget-steps 1,5,10,25,50

# Web server
python -m src.web.app

# Train ML model
python -m src.ml.build_recommender train --league Settlers
```

---

## Resources

- **NSGA-II Paper:** Deb et al. "A Fast and Elitist Multiobjective Genetic Algorithm"
- **Plotly Docs:** https://plotly.com/python/
- **FastAPI Tutorial:** https://fastapi.tiangolo.com/
- **scikit-learn:** https://scikit-learn.org/

---

## Conclusion

Phase 6 features transform the optimizer from a tool into a platform. Pick features that provide the most value to your users and iterate based on feedback.

**Remember:** Perfect is the enemy of good. Ship core features, get feedback, iterate.

---

**Ready to innovate?** Pick your favorite feature and start building!
