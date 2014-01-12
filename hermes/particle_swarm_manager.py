import random

from extra_utils.variety_utils import log_traceback

from NITS_CODE import settings
from hermes import models

@log_traceback
def initialize_particles(count = 8, max_x1 = 2000, min_x1 =0, max_x2 = 3000, min_x2 = 0):
    """
    Initialize a set of particles for finding the optimial isochrone size
    @input count : the number of particles
    """

    #Delete any existing particles from old simulations
    particles = models.Particle.objects.all()
    if particles.count() > 0:
        particles.delete()

    #Get System Flags
    SystemFlags = models.SystemFlags.objects.all()
    SystemFlags = SystemFlags[0]
    simulation_code = SystemFlags.simulation_code
    simulation_set= SystemFlags.simulation_set
    if not simulation_set:
        SystemFlags.simulation_set = 1
    else:
        SystemFlags.simulation_set += 1
    SystemFlags.save()

    #Manual Setup
    if settings.MANUAL_PSO_INITIALIZATION:
        return #do stuff
    else:
    #Random Setup
        for i in range(count):
            x1 = int(random.uniform(min_x1, max_x1))
            x2 = int(random.uniform(min_x2, max_x2))
           
            particle = models.Particle.objects.create(particle_id = i, simulation_set = simulation_set, simulation_code = simulation_code, x1 = x1, x2 = x2, v1 = 0, v2 = 0, step = 0, cost = None, best_cost = None, best_x1 = x1, best_x2 = x2)

            particle.save()

@log_traceback
def get_current_particle():
    
    particles = models.Particle.objects.all().order_by('step')
    current_step = particles[0].step
    particles = models.Particle.objects.filter(step = current_step).order_by('particle_id')
    particle = particles[0]

    #If the velocity of this particles is zero, then it didn't move.  There is no reason to rerun the simulation. simply update the step and recall get_current_particle
    if particle.v1 == 0 and particle.v2 == 0 and not(particle.cost == None): 
        update_particle(particle, particle.cost)
        return get_current_particle()

    return particle
    

@log_traceback
def update_particle(particle, cost):
    """
    Called after a simulation was run to update the costs, x1,x2,v1,v2, and step of a particle
    """

    c1 = 1
    c2 = 1

    particles = models.Particle.objects.exclude(best_cost__isnull = True).order_by('best_cost')
    if particles.count() > 0:
        best_particle = particles[0]
    else:
        best_particle = particle

    if cost < best_particle.best_cost:
        best_particle = particle

    particle.step += 1
    particle.cost = cost

    print particle.x1
    print particle.x2
    if cost < particle.best_cost or particle.best_cost == None:
        particle.best_cost = cost
        particle.best_x1 = particle.x1
        particle.best_x2 = particle.x2
        
    r0 = random.uniform(0.5,1.5)
    r1 = random.uniform(0,1)
    r2 = random.uniform(0,1)
    print r1, c1
    print r2, c2

    print '---besties---'
    print best_particle.x1
    print best_particle.x2
    print best_particle.best_cost
    
    v1 = r0*particle.v1 + r1*c1*(particle.best_x1 - particle.x1) + r2*c2*(best_particle.x1 - particle.x1)
    print v1
    v2 = r0*particle.v2 + r1*c1*(particle.best_x2 - particle.x2) + r2*c2*(best_particle.x2 - particle.x2)
    print v2

    x1 = particle.x1 + v1
    x2 = particle.x2 + v2
    print x1
    print x2
    print '------'

    if x1 < 0:
        x1 = 0
    if x2 < 0:
        x2 = 0
    if settings.CHECK_RADIUS and (x1 < x2):
        x1 = x2

    particle.x1 = x1
    particle.x2 = x2
    
    particle.v1 = v1
    particle.v2 = v2

    particle.save()
    return particle
