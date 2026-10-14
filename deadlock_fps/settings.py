from dataclasses import dataclass, asdict
@dataclass
class Settings:
    preset: str = 'performance'
    level: int = 80
    fps: int = 0
    textures: int = 4
    shadows: bool = False
    fog: bool = False
    bloom: bool = False
    ao: bool = False
    particles: int = 0
    cpu: bool = True
    engine: bool = True
    mods: tuple = ()
    aspect_ratio: float | None = None
    def validate(self):
        if type(self.level) is not int or not 0<=self.level<=100 or not 0<=self.textures<=4 or not 0<=self.particles<=2 or not 0<=self.fps<=500:
            raise ValueError('Graphics settings outside allowed range')
        if self.aspect_ratio is not None and (type(self.aspect_ratio) not in (int,float) or not 1.78<=self.aspect_ratio<=3.50):
            raise ValueError('نسبة الأبعاد يجب أن تكون بين 1.78 و3.50.')
        if 'names' in self.mods and 'health' in self.mods: raise ValueError('مود إزالة الأسماء يتعارض مع مود شريط الصحة القديم؛ اختر أحدهما.')
        if any(m not in MODS for m in self.mods): raise ValueError('Unknown mod')
    @classmethod
    def at_level(cls,level,**kwargs):
        level=max(0,min(100,int(level)))
        return cls(level=level,textures=min(4,level//20),shadows=level<35,
                   fog=level<45,bloom=level<20,ao=level<30,
                   particles=2 if level<35 else (1 if level<60 else 0),cpu=level>=50,**kwargs)
    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls, data):
        # 1.0.0 profile imports deliberately discard every old resolution control.
        data = {k:v for k,v in data.items() if k not in {'scale','width','height'}}
        result=cls(**data);result.validate();return result

MODS = {
 'daylock': ('pak01_dir.vpk - daylock','Daylock','إضاءة نهارية — افحص وضوح الخريطة'),
 'names': ('pak02_dir.vpk - Remove Name Tags','Remove Name Tags','إخفاء أسماء اللاعبين'),
 'health': ('pak03_dir.vpk - Old Healthbars','Old Healthbars','شريط الصحة القديم'),
 'sinner': ('pak26_dir.vpk - Sinner Fix','Sinner Fix','تعديل Sinner المرفق — تأثيره غير موثق'),
}
PRESETS={
 'balanced': Settings.at_level(25,preset='balanced'),
 'performance': Settings.at_level(80,preset='performance'),
 'ultra': Settings.at_level(100,preset='ultra'),
}

LEVELS=[(0,'جودة أعلى','جهاز قوي • تفاصيل أكثر وحمل أكبر على الجهاز'),
 (20,'تخفيف بسيط','جهاز متوسط • خامات أخف وإلغاء الوهج'),
 (40,'تخفيف متوسط','جهاز ضعيف • تقليل الظلال والتظليل والجزيئات'),
 (60,'تخفيف قوي','جهاز ضعيف جدًا • تعطيل الضباب وتقليل الحطام والقوائم'),
 (80,'تخفيف عنيف • الأساسي','أبسط خامات • إضاءة وأعشاب ومؤثرات أقل من ملفك'),
 (100,'أقصى تخفيف','تفاصيل شديدة الانخفاض • قد يقل وضوح بعض المؤثرات')]
def level_info(level):return next((name,desc) for threshold,name,desc in reversed(LEVELS) if level>=threshold)

def values(s):
    s.validate()
    video={
      'setting.r_texture_stream_mip_bias':str(s.textures),
      'setting.r_citadel_shadow_quality':str(int(s.shadows)), 'setting.r_citadel_fog_quality':str(int(s.fog)),
      'setting.r_citadel_ssao_quality':str(int(s.ao)), 'setting.r_effects_bloom':str(s.bloom).lower(),
      'setting.r_post_bloom':str(s.bloom).lower(), 'setting.r_depth_of_field':'false',
      'setting.r_citadel_motion_blur':'0','setting.mat_vsync':'0','setting.r_low_latency':'1',
      'setting.r_particle_max_detail_level':str(s.particles), 'setting.useadvanced':'1',
      'setting.fps_max':str(s.fps),
    }
    convars={'fps_max':str(s.fps),'fps_max_ui':'60','r_texture_stream_mip_bias':str(s.textures),
      'r_particle_max_detail_level':str(s.particles),'r_citadel_half_res_noisy_effects':'true',
      'r_shadows':str(int(s.shadows)),'r_citadel_shadow_quality':str(int(s.shadows)),
      'lb_enable_shadow_casting':str(s.shadows).lower(),'r_enable_volume_fog':str(s.fog).lower(),
      'r_enable_cubemap_fog':str(s.fog).lower(),'r_enable_gradient_fog':str(s.fog).lower(),
      'r_citadel_ssao_quality':str(int(s.ao)),'r_effects_bloom':str(int(s.bloom)),
      'r_post_bloom':str(int(s.bloom)),'r_depth_of_field':'0',
      'r_particle_shadows':str(int(s.shadows)),'r_particle_cables_cast_shadows':str(int(s.shadows))}
    if s.cpu: convars.update({'cl_ragdoll_limit':'1','props_break_max_pieces_perframe':'1',
      'panorama_max_fps':'30','panorama_max_overlay_fps':'30','panorama_allow_transitions':'false','panorama_disable_blur':'true'})
    scene={'CSMCascadeResolution':'2048' if s.shadows else '0',
      'DefaultShadowTextureWidth':'6144' if s.shadows else '0',
      'DefaultShadowTextureHeight':'6144' if s.shadows else '0',
      'VolumetricFog':str(int(s.fog)),'CubemapFog':str(int(s.fog)),'NonTexturedGradientFog':str(int(s.fog))}
    # Selected runtime graphics scalars from the supplied source, not its old engine schema.
    if s.level>=60:
        convars.update({'r_grass_quality':'0','sc_clutter_enable':'false','r_drawropes':'false',
            'r_world_wind_strength':'0','r_RainParticleDensity':'0','r_texturefilteringquality':'0',
            'r_particle_depth_feathering':'false','r_dashboard_render_quality':'1',
            'cl_show_splashes':'0','violence_ablood':'0','violence_agibs':'0','violence_hblood':'0','violence_hgibs':'0'})
        video.update({'setting.r_particle_depth_feathering':'false','setting.r_citadel_half_res_noisy_effects':'true',
            'setting.r_arealights':'false','setting.r_displacement_mapping':'0'})
    if s.level>=80:
        convars.update({'lb_enable_dynamic_lights':'false','lb_enable_baked_shadows':'false',
            'lb_enable_stationary_lights':'false','fog_enable':'false','fog_enableskybox':'false',
            'volume_fog_enable_jitter':'false','r_ssao':'0','r_ssao_strength':'0',
            'r_grass_start_fade':'0','r_grass_end_fade':'0','r_particle_explicit_fetch':'false',
            'r_particle_max_texture_layers':'4','cloth_sim_on_tick':'0',
            'panorama_panel_occlusion':'true','r_texture_budget_threshold':'0.7','r_texture_budget_update_period':'0.5'})
        video.update({'setting.csm_max_shadow_dist_override':'0','setting.csm_max_num_cascades_override':'0',
            'setting.csm_viewmodel_shadows':'0','setting.lb_enable_shadow_casting':'false',
            'setting.lb_dynamic_shadow_resolution':'false','setting.r_citadel_distancefield_ao_quality':'0'})
        scene.update({'FogCachedShadowAtlasWidth':'0','FogCachedShadowAtlasHeight':'0','FogCachedShadowTileSize':'0'})
    if s.level>=90:
        convars.update({'cl_particle_fallback_base':'5','cl_particle_fallback_multiplier':'10',
            'cl_particle_sim_fallback_base_multiplier':'100','cl_particle_sim_fallback_threshold_ms':'1',
            'r_update_particles_on_render_only_frames':'true'})
        video.update({'setting.cl_particle_fallback_base':'6','setting.cl_particle_fallback_multiplier':'4'})
    if s.aspect_ratio is not None:convars['r_aspectratio']=f'{s.aspect_ratio:.2f}'
    return video,convars,scene

TEXTURE_LABELS = ["خامات مفصلة", "تخفيف بسيط", "تخفيف متوسط", "خامات بسيطة", "أبسط خامات • أقصى تخفيف"]
