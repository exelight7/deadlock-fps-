"""What each setting does, in plain words. Written for this project.

The facts about Valve's game (does the setting still exist, can gameinfo.gi change it, what is Valve's default) live in
facts.py and are generated from Valve's data. Nothing here is copied from another tool: the sentences describe what a
setting controls, and the "sight" mark says that turning it down can change how much of the world you can see.
"""
from dataclasses import dataclass

from ..i18n import tr
from .facts import FACTS

ACTIVE, REMOVED, BLOCKED, CHEAT, UNVERIFIED = 'active', 'removed', 'blocked', 'cheat', 'unverified'
IGNORED = (REMOVED, BLOCKED)            # statuses where the game should not apply the line at all

# Controls that have their own place in the interface, so a level never decides them and they cannot be left out here.
PROTECTED = frozenset({'fps_max', 'fps_max_ui', 'r_aspectratio'})

CATEGORIES = {
    'shadows': tr('Shadows'),
    'lighting': tr('Fog and lighting'),
    'post': tr('Screen effects'),
    'textures': tr('Textures and detail'),
    'particles': tr('Particles and effects'),
    'world': tr('Grass, clutter and distance'),
    'interface': tr('Menus and interface'),
    'physics': tr('Physics and animation'),
    'audio': tr('Audio'),
    'gore': tr('Blood and gibs'),
    'screen': tr('Frame rate and screen'),
}

STATUS_LABELS = {
    ACTIVE: tr('Works'),
    BLOCKED: tr('Blocked'),
    REMOVED: tr('Removed'),
    CHEAT: tr('Cheat-only'),
    UNVERIFIED: tr('Unverified'),
}
STATUS_TEXT = {
    ACTIVE: tr("Valve's data lists this setting and nothing blocks it."),
    BLOCKED: tr("Valve's data says gameinfo.gi cannot change this setting, so the game should ignore this line."),
    REMOVED: tr("Valve's data no longer has this setting, so this line does nothing."),
    CHEAT: tr('Valve marks this as a cheat command. Whether the game applies it from gameinfo.gi is not documented, so its effect is uncertain.'),
    UNVERIFIED: tr("This setting is not in Valve's data, so its effect cannot be confirmed."),
}

# (name, category, what it controls, may change what you can see)
_ROWS = (
    ('cl_particle_fallback_base', 'particles', tr('Makes effects switch to cheaper versions when the game is under load (the starting point).'), False),
    ('cl_particle_fallback_multiplier', 'particles', tr('Makes effects switch to cheaper versions when the game is under load (how strongly).'), False),
    ('cl_particle_sim_fallback_base_multiplier', 'particles', tr('How aggressively effects drop to cheaper versions once they take too long.'), False),
    ('cl_particle_sim_fallback_threshold_ms', 'particles', tr('How long effects may take to update before new ones use cheaper versions.'), False),
    ('cl_ragdoll_limit', 'physics', tr('Maximum number of falling bodies shown at once.'), False),
    ('cl_show_splashes', 'particles', tr('Water and impact splash effects.'), False),
    ('cloth_sim_on_tick', 'physics', tr('Whether cloth is simulated on every game tick.'), False),
    ('csm_max_num_cascades_override', 'shadows', tr('Number of layers used for sunlight shadows.'), False),
    ('csm_max_shadow_dist_override', 'shadows', tr('How far sunlight shadows reach.'), False),
    ('csm_viewmodel_shadows', 'shadows', tr('Sunlight shadows cast by your own weapon and hands.'), False),
    ('enable_boneflex', 'physics', tr('Small automatic movement in faces and some models.'), False),
    ('fog_enable', 'lighting', tr('Master switch for fog.'), True),
    ('fog_enableskybox', 'lighting', tr('Fog on the sky.'), False),
    ('fps_max', 'screen', tr('Frame-rate limit (0 means no limit). It comes from the frame-rate slider, not from the level.'), False),
    ('fps_max_ui', 'screen', tr('Frame-rate limit while a menu is open.'), False),
    ('lb_dynamic_shadow_resolution', 'shadows', tr('Lets the game change shadow detail on the fly.'), False),
    ('lb_enable_baked_shadows', 'shadows', tr('Pre-calculated shadows from fixed lights.'), False),
    ('lb_enable_dynamic_lights', 'lighting', tr('Lights that move or change while you play.'), False),
    ('lb_enable_shadow_casting', 'shadows', tr('Whether moving and fixed lights cast shadows.'), False),
    ('lb_enable_stationary_lights', 'lighting', tr('Fixed lights.'), False),
    ('mat_vsync', 'screen', tr('Vertical sync (off gives lower delay, but the picture can tear).'), False),
    ('panorama_allow_transitions', 'interface', tr('Animated transitions in the shop and menus.'), False),
    ('panorama_disable_blur', 'interface', tr('Turns off blur effects in the interface.'), False),
    ('panorama_max_fps', 'interface', tr('Frame-rate limit of the interface.'), False),
    ('panorama_max_overlay_fps', 'interface', tr('Frame-rate limit of interface overlays.'), False),
    ('panorama_panel_occlusion', 'interface', tr('Skips work for interface panels hidden behind others.'), False),
    ('props_break_max_pieces_perframe', 'physics', tr('How many pieces breaking objects may create per frame.'), False),
    ('r_RainParticleDensity', 'particles', tr('How dense the rain is.'), False),
    ('r_arealights', 'lighting', tr('Area lights (soft lights that have a shape).'), False),
    ('r_aspectratio', 'screen', tr('Picture shape: a wider value shows more of the world sideways. It comes from the View width control.'), True),
    ('r_citadel_distancefield_ao_quality', 'post', tr('Quality of the soft shading computed from distance fields.'), False),
    ('r_citadel_distancefield_farfield_enable', 'lighting', tr('Distance-field lighting far away.'), False),
    ('r_citadel_fog_quality', 'lighting', tr('Fog quality from the video menu.'), True),
    ('r_citadel_half_res_noisy_effects', 'particles', tr('Draws noisy effects at half resolution.'), False),
    ('r_citadel_motion_blur', 'post', tr('Motion blur.'), False),
    ('r_citadel_shadow_quality', 'shadows', tr('Shadow quality from the video menu (0 is the lowest).'), False),
    ('r_citadel_ssao', 'post', tr('The ambient-occlusion switch stored in video.txt.'), False),
    ('r_citadel_ssao_quality', 'post', tr('Ambient-occlusion quality from 0 (off) to 4. The choice made in the video menu, stored in video.txt, wins over gameinfo.gi.'), False),
    ('r_dashboard_render_quality', 'interface', tr('Render quality of the main-menu dashboard.'), False),
    ('r_depth_of_field', 'post', tr('Depth-of-field blur.'), False),
    ('r_displacement_mapping', 'textures', tr('Bumps made from real geometry on surfaces.'), False),
    ('r_drawropes', 'world', tr('Draws ropes and cables.'), True),
    ('r_effects_bloom', 'post', tr('Glow around abilities and particles.'), False),
    ('r_enable_cubemap_fog', 'lighting', tr('Fog taken from reflection maps.'), True),
    ('r_enable_gradient_fog', 'lighting', tr('Simple gradient fog.'), True),
    ('r_enable_volume_fog', 'lighting', tr('Volumetric fog (fog with depth and light shafts).'), True),
    ('r_grass_end_fade', 'world', tr('Distance at which grass has faded out completely.'), True),
    ('r_grass_quality', 'world', tr('Grass quality (0 is off, 4 is ultra).'), True),
    ('r_grass_start_fade', 'world', tr('Distance at which grass starts to fade.'), True),
    ('r_low_latency', 'screen', tr('Asks NVIDIA Low Latency or AMD Anti-Lag to cut input delay.'), False),
    ('r_particle_cables_cast_shadows', 'shadows', tr('Lets rope and cable effects cast shadows.'), False),
    ('r_particle_depth_feathering', 'particles', tr('Soft edges where particles meet surfaces.'), False),
    ('r_particle_explicit_fetch', 'particles', tr('A way of drawing particles.'), False),
    ('r_particle_max_detail_level', 'particles', tr('Maximum detail of particle effects (0 to 3).'), False),
    ('r_particle_max_texture_layers', 'particles', tr('Caps how many texture layers one particle uses.'), False),
    ('r_particle_shadows', 'shadows', tr('Shadows cast by particles.'), False),
    ('r_physics_particle_op_spawn_scale', 'particles', tr('How many particles physics creates (0 stops them).'), False),
    ('r_post_bloom', 'post', tr('Full-screen bloom.'), False),
    ('r_shadows', 'shadows', tr('Master switch for shadows.'), False),
    ('r_size_cull_threshold', 'world', tr('Objects smaller than this share of the screen are not drawn.'), True),
    ('r_ssao', 'post', tr('Ambient occlusion (soft shading in corners and creases).'), False),
    ('r_ssao_strength', 'post', tr('Strength of ambient occlusion (0 removes it).'), False),
    ('r_texture_budget_threshold', 'textures', tr('How full the texture memory may get before textures shrink.'), False),
    ('r_texture_budget_update_period', 'textures', tr('How often texture memory use is checked.'), False),
    ('r_texture_stream_mip_bias', 'textures', tr('How blurry streamed textures may be (higher means smaller, blurrier textures).'), False),
    ('r_texturefilteringquality', 'textures', tr('Texture filtering, from 0 (bilinear) to 5 (anisotropic 16x).'), False),
    ('r_update_particles_on_render_only_frames', 'particles', tr('Updates particles on frames that draw without a game tick.'), False),
    ('r_world_wind_strength', 'world', tr('Wind that sways grass and trees (0 stops it).'), False),
    ('sc_clutter_enable', 'world', tr('Small clutter objects scattered on the ground.'), True),
    ('snd_occlusion_bounces', 'audio', tr('How many sound bounces are traced when walls muffle sound.'), False),
    ('snd_occlusion_rays', 'audio', tr('How many rays are traced when walls muffle sound (0 turns it off).'), False),
    ('snd_steamaudio_max_occlusion_samples', 'audio', tr('Maximum rays Steam Audio traces for volumetric muffling.'), False),
    ('snd_steamaudio_num_diffuse_samples', 'audio', tr('Number of directions Steam Audio considers when sound bounces.'), False),
    ('useadvanced', 'screen', tr('A video.txt switch for custom video settings.'), False),
    ('violence_ablood', 'gore', tr('Alien blood.'), False),
    ('violence_agibs', 'gore', tr('Alien gibs.'), False),
    ('violence_hblood', 'gore', tr('Human blood.'), False),
    ('violence_hgibs', 'gore', tr('Human gibs.'), False),
    ('volume_fog_enable_jitter', 'lighting', tr('Shakes volumetric fog samples between frames to hide banding.'), False),
    # SceneSystem section of gameinfo.gi
    ('CSMCascadeResolution', 'shadows', tr('Sunlight shadow detail (texture size).'), False),
    ('CharacterDecals', 'textures', tr('Marks drawn on characters.'), False),
    ('CubemapFog', 'lighting', tr('Fog taken from reflection maps (scene setting).'), True),
    ('DefaultShadowTextureHeight', 'shadows', tr('Height of the shadow texture: smaller is cheaper and blurrier.'), False),
    ('DefaultShadowTextureWidth', 'shadows', tr('Width of the shadow texture: smaller is cheaper and blurrier.'), False),
    ('FogCachedShadowAtlasHeight', 'lighting', tr('Height of the cache used for fog shadows.'), False),
    ('FogCachedShadowAtlasWidth', 'lighting', tr('Width of the cache used for fog shadows.'), False),
    ('FogCachedShadowTileSize', 'lighting', tr('Tile size of the cache used for fog shadows.'), False),
    ('HairShading', 'textures', tr('Detailed lighting on hair.'), False),
    ('NonTexturedGradientFog', 'lighting', tr('Plain gradient fog (scene setting).'), True),
    ('PerVertexLighting', 'lighting', tr('Lighting calculated at model corners instead of per pixel.'), False),
    ('PointLightShadowsEnabled', 'shadows', tr('Shadows from small point lights.'), False),
    ('PunctualContactShadows', 'shadows', tr('Fine shadows where objects touch.'), False),
    ('SelfShadowStrength', 'shadows', tr('How strongly characters shade themselves.'), False),
    ('ShadowmapMaxFilterRadius', 'shadows', tr('How soft the edges of shadows are.'), False),
    ('VolumetricFog', 'lighting', tr('Volumetric fog (scene setting).'), True),
)


@dataclass(frozen=True)
class Entry:
    name: str
    category: str
    effect: str
    status: str
    since: int          # the build in which Valve stopped listing it (0: unknown or not applicable)
    default: str        # Valve's own default value ('' when unknown)
    sight: bool         # turning it down can change how much of the world you can see

    @property
    def ignored(self):
        return self.status in IGNORED

    @property
    def protected(self):
        return self.name in PROTECTED


ENTRIES = {}
for _name, _category, _effect, _sight in _ROWS:
    _status, _since, _default = FACTS[_name]
    ENTRIES[_name] = Entry(_name, _category, _effect, _status, _since, _default, _sight)


def entry_for(name):
    """The Entry for a setting name, or None for a name this table does not know."""
    return ENTRIES.get(name)
