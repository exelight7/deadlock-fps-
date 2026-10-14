from dataclasses import dataclass, asdict
@dataclass
class Settings:
    preset: str = 'performance'
    scale: int = 67
    width: int = 0
    height: int = 0
    fps: int = 120
    textures: int = 3
    shadows: bool = False
    fog: bool = False
    bloom: bool = False
    ao: bool = False
    particles: int = 0
    cpu: bool = True
    engine: bool = True
    mods: tuple = ()
    def validate(self):
        if not 25<=self.scale<=100 or not 0<=self.textures<=4 or not 0<=self.particles<=2 or not 0<=self.fps<=500:
            raise ValueError('Graphics settings outside allowed range')
        if (self.width,self.height)!=(0,0) and not (640<=self.width<=7680 and 480<=self.height<=4320):
            raise ValueError('Invalid resolution')
        if 'names' in self.mods and 'health' in self.mods: raise ValueError('مود إزالة الأسماء يتعارض مع مود شريط الصحة القديم؛ اختر أحدهما.')
        if any(m not in MODS for m in self.mods): raise ValueError('Unknown mod')
    def to_dict(self): return asdict(self)

MODS = {
 'daylock': ('pak01_dir.vpk - daylock','Daylock','إضاءة نهارية — افحص وضوح الخريطة'),
 'names': ('pak02_dir.vpk - Remove Name Tags','Remove Name Tags','إخفاء أسماء اللاعبين'),
 'health': ('pak03_dir.vpk - Old Healthbars','Old Healthbars','شريط الصحة القديم'),
 'sinner': ('pak26_dir.vpk - Sinner Fix','Sinner Fix','تعديل Sinner المرفق — تأثيره غير موثق'),
}
PRESETS={
 'balanced': Settings('balanced',85,textures=1,shadows=True,fog=True,ao=True,particles=2,cpu=False),
 'performance': Settings(),
 'ultra': Settings('ultra',50,1280,720,90,4,False,False,False,False,0,True,True),
}

def values(s):
    s.validate()
    video={
      'setting.mat_viewportscale':f'{s.scale/100:.6f}', 'setting.r_texture_stream_mip_bias':str(s.textures),
      'setting.r_citadel_shadow_quality':str(int(s.shadows)), 'setting.r_citadel_fog_quality':str(int(s.fog)),
      'setting.r_citadel_ssao_quality':str(int(s.ao)), 'setting.r_effects_bloom':str(s.bloom).lower(),
      'setting.r_post_bloom':str(s.bloom).lower(), 'setting.r_depth_of_field':'false',
      'setting.r_citadel_motion_blur':'0','setting.mat_vsync':'0','setting.r_low_latency':'1',
      'setting.r_particle_max_detail_level':str(s.particles), 'setting.useadvanced':'1',
      'setting.r_citadel_upscaling':'0','setting.fps_max':str(s.fps),
    }
    if s.width: video.update({'setting.defaultres':str(s.width),'setting.defaultresheight':str(s.height)})
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
    return video,convars,scene
