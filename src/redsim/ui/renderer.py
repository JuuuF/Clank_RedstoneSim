"""OpenGL drawing with PySide6's own GL wrappers (no PyOpenGL; doc/decisions.md ADR-002).

One shader draws four kinds of vertex streams: opaque triangles, translucent triangles
(drawn after, without depth writes), lines (outlines, sections) and lines drawn on top of
everything (the camera pivot). The world mesh is
split into chunks (``redsim.ui.geometry.ChunkedMesh``), each with its own buffers, so a change
re-uploads only the chunks it touched. Vertices are ``x, y, z, r, g, b, a, u, v`` float32
(``u`` < 0: untextured; 7-column data is padded). Textured faces sample the block atlas
(``atlas.Atlas``) with nearest filtering; texels with alpha < 0.1 are discarded.
"""

from __future__ import annotations

import time

import numpy as np
from PySide6.QtGui import (
    QImage,
    QMatrix4x4,
    QOpenGLContext,
    QOpenGLFunctions,
    QVector2D,
    QVector3D,
    QVector4D,
)
from PySide6.QtOpenGL import (
    QOpenGLBuffer,
    QOpenGLShader,
    QOpenGLShaderProgram,
    QOpenGLTexture,
    QOpenGLVertexArrayObject,
)
from shiboken6 import Shiboken

GL_FLOAT = 0x1406
GL_TRIANGLES = 0x0004
GL_LINES = 0x0001
GL_TEXTURE0 = 0x84C0
GL_DEPTH_TEST = 0x0B71
GL_BLEND = 0x0BE2
GL_SRC_ALPHA = 0x0302
GL_ONE_MINUS_SRC_ALPHA = 0x0303
GL_COLOR_BUFFER_BIT = 0x4000
GL_DEPTH_BUFFER_BIT = 0x0100
GL_FALSE = 0
GL_TRUE = 1
GL_POLYGON_OFFSET_FILL = 0x8037
GL_SCISSOR_TEST = 0x0C11
GL_STENCIL_TEST = 0x0B90
GL_CULL_FACE = 0x0B44
GL_LEQUAL = 0x0203
#: Vertex stride: x, y, z, r, g, b, a, u, v as float32.
STRIDE = 36

VERTEX_SHADER = """#version 330 core
layout(location = 0) in vec3 position;
layout(location = 1) in vec4 color;
layout(location = 2) in vec2 uv;
uniform mat4 mvp;
out vec4 vColor;
out vec2 vUv;
out vec3 vWorld;
void main() {
    gl_Position = mvp * vec4(position, 1.0);
    vColor = color;
    vUv = uv;
    vWorld = position;  // the fog distance is per fragment: exact on large faces too
}
"""
FRAGMENT_SHADER = """#version 330 core
in vec4 vColor;
in vec2 vUv;
in vec3 vWorld;
uniform vec3 eye;
uniform float alphaScale;
uniform vec3 fogColor;
uniform vec2 fogRange;   // start, end (blocks)
uniform float fogAmount; // 0 for overlays, 1 for the world
uniform sampler2D atlas;
uniform sampler2D clouds;
uniform vec2 cloudOffset;  // blocks: the clouds drift
uniform vec4 groundTile;   // atlas rect of the ground texture; zero width: untextured
uniform vec3 groundAverage; // its average color, for the distance (no mipmaps)
out vec4 fragColor;
void main() {
    vec4 base = vColor;
    if (vUv.x < -2.5) {  // clouds: one texel per 12 blocks, like the game
        vec4 texel = texture(clouds, (vWorld.xz + cloudOffset) / 3072.0);
        if (texel.a < 0.1) discard;
        base = vec4(texel.rgb, texel.a) * vColor;
    } else if (vUv.x < -1.5 && groundTile.z > 0.0) {  // the ground: the texture repeats per block
        vec2 uv = groundTile.xy + fract(vWorld.xz) * groundTile.zw;
        vec3 near = texture(atlas, uv).rgb;
        float far = smoothstep(16.0, 64.0, distance(vWorld, eye));
        base = vec4(mix(near, groundAverage, far) * vColor.rgb, 1.0);
    } else if (vUv.x >= 0.0) {  // textured: the game's texture, tinted and shaded by the color
        vec4 texel = texture(atlas, vUv);
        if (texel.a < 0.1) discard;  // cutout (dust, torches, rails, glass)
        base = texel * vColor;
    }
    float fog = clamp((distance(vWorld, eye) - fogRange.x) / (fogRange.y - fogRange.x), 0.0, 1.0);
    vec3 rgb = mix(base.rgb, fogColor, fog * fogAmount);
    fragColor = vec4(rgb, base.a * alphaScale);
}
"""
#: Sky gradient (top of the screen, horizon); the fog fades the world into the horizon.
SKY_TOP = (0.42, 0.62, 0.92)
SKY_HORIZON = (0.72, 0.83, 0.96)
#: The ground around the floor, like a superflat world fading into the horizon: just
#: below the floor's top (hidden under it), out to where the fog hides its edge.
GROUND_COLOR = (0.40, 0.53, 0.29)  # without the game's textures: a muted grass green
GROUND_SHADE = (0.50, 0.66, 0.31)  # the plains grass color, a little darker
GROUND_TEXTURE = "minecraft:block/grass_block_top"
#: Clouds: the game's texture on a plane high above the floor, drifting along x.
CLOUD_TEXTURE = "minecraft:environment/clouds"
CLOUD_Y = 112.0
CLOUD_COLOR = (1.0, 1.0, 1.0, 0.8)
CLOUD_SPEED = 0.6  # blocks per second
GROUND_Y = 0.98
GROUND_REACH = 900.0  # inside the far plane (1000)
#: Alpha of the parts of selection overlays hidden behind blocks.
HIDDEN_OVERLAY_ALPHA = 0.4


def _plane(y: float, color: tuple[float, ...], marker: float) -> np.ndarray:
    """A horizontal square of side 2 × ``GROUND_REACH`` at height ``y`` (two triangles),
    with ``marker`` as both UV coordinates: it selects the shader branch."""
    r, m = GROUND_REACH, (marker, marker)
    corners = [(-r, -r), (r, -r), (r, r), (-r, -r), (r, r), (-r, r)]
    return np.array([(x, y, z, *color, *m) for x, z in corners], dtype=np.float32)


def _forget_texture(texture: QOpenGLTexture) -> None:
    """Free the texture's GPU storage (call with its context current) and detach the
    Python wrapper, so the C++ destructor never runs later: it asks the texture's context
    about sharing, and a garbage-collected texture whose context was already gone crashed
    the process (seen in test runs)."""
    texture.destroy()
    Shiboken.invalidate(texture)


class _Stream:
    def __init__(self) -> None:
        self.vao = QOpenGLVertexArrayObject()
        self.vao.create()
        self.vbo = QOpenGLBuffer(QOpenGLBuffer.Type.VertexBuffer)
        self.vbo.create()
        self.count = 0

    def upload(self, program: QOpenGLShaderProgram, data: np.ndarray) -> None:
        if data.ndim == 2 and data.shape[1] == 7:  # untextured: UV (-1, -1)
            data = np.hstack([data, np.full((len(data), 2), -1.0, dtype=np.float32)])
        data = np.ascontiguousarray(data, dtype=np.float32)
        self.count = len(data)
        self.vao.bind()
        self.vbo.bind()
        self.vbo.allocate(data.tobytes(), data.nbytes)
        program.enableAttributeArray(0)
        program.setAttributeBuffer(0, GL_FLOAT, 0, 3, STRIDE)
        program.enableAttributeArray(1)
        program.setAttributeBuffer(1, GL_FLOAT, 12, 4, STRIDE)
        program.enableAttributeArray(2)
        program.setAttributeBuffer(2, GL_FLOAT, 28, 2, STRIDE)
        self.vao.release()

    def destroy(self) -> None:
        self.vbo.destroy()
        self.vao.destroy()


class Renderer:
    """Owns GL resources; must be created and used with the widget's context current."""

    def __init__(self) -> None:
        context = QOpenGLContext.currentContext()
        assert context is not None, "a current OpenGL context is required"
        self.gl: QOpenGLFunctions = context.functions()
        self.program = QOpenGLShaderProgram()
        self.program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Vertex, VERTEX_SHADER)
        self.program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Fragment, FRAGMENT_SHADER)
        if not self.program.link():
            raise RuntimeError(self.program.log())
        self.program.bind()
        self.atlas: QOpenGLTexture | None = None
        #: Chunk key → (opaque, translucent, solid) streams.
        self.chunks: dict[object, tuple[_Stream, _Stream, _Stream]] = {}
        self.lines = _Stream()
        self.top_lines = _Stream()
        self.ghost = _Stream()  # translucent preview of a moved or pasted selection
        #: Selection box edges and handles (triangles): drawn normally, then again on top
        #: of everything at reduced alpha so hidden parts stay visible ("x-ray").
        self.overlay = _Stream()
        self.sky = _Stream()
        self._sky_horizon: float | None = None
        self._upload_sky(-1.0)
        self.volume = _Stream()  # faint translucent selection body
        self.clouds: QOpenGLTexture | None = None
        self.cloud_plane = _Stream()  # UV marker -3: the shader samples the cloud texture
        self.cloud_plane.upload(self.program, _plane(CLOUD_Y, CLOUD_COLOR, -3.0))
        self.ground = _Stream()
        self.ground_tile = (0.0, 0.0, 0.0, 0.0)
        self.ground_average = (0.0, 0.0, 0.0)
        self._upload_ground(GROUND_COLOR)

    def set_chunk(
        self, key: object, opaque: np.ndarray, translucent: np.ndarray, solid: np.ndarray
    ) -> None:
        streams = self.chunks.get(key)
        if streams is None:
            streams = self.chunks[key] = (_Stream(), _Stream(), _Stream())
        self.program.bind()
        streams[0].upload(self.program, opaque)
        streams[1].upload(self.program, translucent)
        streams[2].upload(self.program, solid)

    def _upload_sky(self, horizon: float) -> None:
        """The sky behind everything, in screen space: the fog's color up to the horizon
        line (``horizon``: its height in normalized device coordinates), so ground and
        sky meet without a seam, then a gradient to the zenith color at the top."""
        horizon = max(-1.0, min(1.0, horizon))
        if horizon == self._sky_horizon:
            return
        self._sky_horizon = horizon
        low, top = (*SKY_HORIZON, 1.0), (*SKY_TOP, 1.0)
        rows = []
        for y0, y1, c0, c1 in ((-1.0, horizon, low, low), (horizon, 1.0, low, top)):
            rows += [(-1, y0, 0.0, *c0), (1, y0, 0.0, *c0), (1, y1, 0.0, *c1)]
            rows += [(-1, y0, 0.0, *c0), (1, y1, 0.0, *c1), (-1, y1, 0.0, *c1)]
        self.sky.upload(self.program, np.array(rows, dtype=np.float32))

    def _upload_ground(self, color: tuple[float, float, float]) -> None:
        # UV marker -2: the shader tiles the ground texture.
        self.ground.upload(self.program, _plane(GROUND_Y, (*color, 1.0), -2.0))

    def set_ground(
        self, tile: tuple[float, float, float, float] | None, average: tuple[float, ...]
    ) -> None:
        """The ground texture's atlas rect and average color; None: a plain color."""
        self.ground_tile = tile or (0.0, 0.0, 0.0, 0.0)
        self.ground_average = (average[0], average[1], average[2])
        self._upload_ground(GROUND_SHADE if tile else GROUND_COLOR)

    def set_clouds(self, image: QImage | None) -> None:
        """The game's cloud texture (repeating, sharp), or None for no clouds."""
        if self.clouds is not None:
            _forget_texture(self.clouds)
            self.clouds = None
        if image is None:
            return
        texture = QOpenGLTexture(image, QOpenGLTexture.MipMapGeneration.DontGenerateMipMaps)
        texture.setMinificationFilter(QOpenGLTexture.Filter.Nearest)
        texture.setMagnificationFilter(QOpenGLTexture.Filter.Nearest)
        texture.setWrapMode(QOpenGLTexture.WrapMode.Repeat)
        self.clouds = texture

    def set_atlas(self, image: QImage | None) -> None:
        """The block texture atlas (nearest-neighbor sampling, like the game)."""
        if self.atlas is not None:
            _forget_texture(self.atlas)
            self.atlas = None
        if image is None:
            return
        texture = QOpenGLTexture(image, QOpenGLTexture.MipMapGeneration.DontGenerateMipMaps)
        texture.setMinificationFilter(QOpenGLTexture.Filter.Nearest)
        texture.setMagnificationFilter(QOpenGLTexture.Filter.Nearest)
        texture.setWrapMode(QOpenGLTexture.WrapMode.ClampToEdge)
        self.atlas = texture

    def remove_chunk(self, key: object) -> None:
        streams = self.chunks.pop(key, None)
        if streams is not None:
            for stream in streams:
                stream.destroy()

    def upload_lines(self, lines: np.ndarray) -> None:
        self.program.bind()
        self.lines.upload(self.program, lines)

    def upload_top_lines(self, lines: np.ndarray) -> None:
        self.program.bind()
        self.top_lines.upload(self.program, lines)

    def upload_ghost(self, triangles: np.ndarray) -> None:
        self.program.bind()
        self.ghost.upload(self.program, triangles)

    def upload_volume(self, triangles: np.ndarray) -> None:
        self.program.bind()
        self.volume.upload(self.program, triangles)

    def upload_overlay(self, triangles: np.ndarray) -> None:
        self.program.bind()
        self.overlay.upload(self.program, triangles)

    def draw(
        self,
        mvp: np.ndarray,
        width: int,
        height: int,
        background: tuple[float, ...],
        xray: int = 0,
        building_alpha: float = 0.30,
        circuit_alpha: float = 0.50,
        eye: tuple[float, float, float] = (0.0, 0.0, 0.0),
        fog: tuple[float, float] = (80.0, 220.0),
        horizon: float = -1.0,
        scenery: bool = True,
    ) -> None:
        """Draw everything. ``xray`` 1: full building blocks become see-through (no depth
        writes) while circuit parts stay opaque; 2: circuit parts are see-through too."""
        gl = self.gl
        # A QPainter overlay drawn after us may leave any of these changed.
        gl.glDisable(GL_SCISSOR_TEST)
        gl.glDisable(GL_STENCIL_TEST)
        gl.glDisable(GL_CULL_FACE)
        gl.glDisable(GL_BLEND)
        gl.glDepthMask(GL_TRUE)
        # Equal depth passes: coplanar overlay faces (grass sides) draw over their base.
        gl.glDepthFunc(GL_LEQUAL)
        gl.glViewport(0, 0, width, height)
        gl.glClearColor(*background)
        gl.glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        program = self.program
        program.bind()
        if self.atlas is not None:
            self.atlas.bind(0)
            program.setUniformValue1i(program.uniformLocation("atlas"), 0)
        if self.clouds is not None:
            self.clouds.bind(1)
            program.setUniformValue1i(program.uniformLocation("clouds"), 1)
            gl.glActiveTexture(GL_TEXTURE0)  # QPainter overlays expect unit 0 active
        drift = (time.monotonic() * CLOUD_SPEED) % 3072.0
        program.setUniformValue(program.uniformLocation("cloudOffset"), QVector2D(drift, 0.0))
        location = program.uniformLocation("mvp")
        alpha = program.uniformLocation("alphaScale")
        fog_amount = program.uniformLocation("fogAmount")
        program.setUniformValue1f(alpha, 1.0)
        program.setUniformValue(program.uniformLocation("eye"), QVector3D(*eye))
        program.setUniformValue(program.uniformLocation("fogColor"), QVector3D(*SKY_HORIZON))
        program.setUniformValue(program.uniformLocation("fogRange"), QVector2D(*fog))
        program.setUniformValue(program.uniformLocation("groundTile"), QVector4D(*self.ground_tile))
        program.setUniformValue(
            program.uniformLocation("groundAverage"), QVector3D(*self.ground_average)
        )
        # Sky: a screen-filling gradient behind everything (no depth).
        program.setUniformValue1f(fog_amount, 0.0)
        program.setUniformValue(location, QMatrix4x4())
        gl.glDisable(GL_DEPTH_TEST)
        gl.glDepthMask(GL_FALSE)
        self._upload_sky(horizon)
        self.sky.vao.bind()
        gl.glDrawArrays(GL_TRIANGLES, 0, self.sky.count)
        gl.glDepthMask(GL_TRUE)
        gl.glEnable(GL_DEPTH_TEST)
        program.setUniformValue(location, QMatrix4x4(*mvp.astype(np.float32).flatten()))
        program.setUniformValue1f(fog_amount, 1.0)
        if scenery:
            self.ground.vao.bind()
            gl.glDrawArrays(GL_TRIANGLES, 0, self.ground.count)
        # World faces are wound counter-clockwise seen from outside, like the game's, which
        # draws them with back-face culling: flat parts (dust, rails) show one side only.
        gl.glEnable(GL_CULL_FACE)
        for opaque, _, solid in self.chunks.values():
            drawn = () if xray == 2 else (opaque,) if xray == 1 else (opaque, solid)
            for stream in drawn:
                if stream.count:
                    stream.vao.bind()
                    gl.glDrawArrays(GL_TRIANGLES, 0, stream.count)
        gl.glDisable(GL_CULL_FACE)
        if self.lines.count:
            program.setUniformValue1f(fog_amount, 0.0)
            gl.glEnable(GL_BLEND)  # guides fade out (per-vertex alpha)
            gl.glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            self.lines.vao.bind()
            gl.glDrawArrays(GL_LINES, 0, self.lines.count)
            gl.glDisable(GL_BLEND)
            program.setUniformValue1f(fog_amount, 1.0)
        if scenery and self.clouds is not None:  # translucent and far: no depth writes
            gl.glEnable(GL_BLEND)
            gl.glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            gl.glDepthMask(GL_FALSE)
            self.cloud_plane.vao.bind()
            gl.glDrawArrays(GL_TRIANGLES, 0, self.cloud_plane.count)
            gl.glDepthMask(GL_TRUE)
            gl.glDisable(GL_BLEND)
        if xray:
            gl.glEnable(GL_CULL_FACE)
            gl.glEnable(GL_BLEND)
            gl.glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            gl.glDepthMask(GL_FALSE)
            layers = [(1, building_alpha)] + ([(0, circuit_alpha)] if xray == 2 else [])
            for index, value in layers:
                self.program.setUniformValue1f(alpha, value)
                for streams in self.chunks.values():
                    stream = streams[2] if index == 1 else streams[0]
                    if stream.count:
                        stream.vao.bind()
                        gl.glDrawArrays(GL_TRIANGLES, 0, stream.count)
            self.program.setUniformValue1f(alpha, 1.0)
            gl.glDepthMask(GL_TRUE)
            gl.glDisable(GL_BLEND)
            gl.glDisable(GL_CULL_FACE)
        world_translucent = [stream for _, stream, _ in self.chunks.values() if stream.count]
        if world_translucent:
            gl.glEnable(GL_CULL_FACE)
            gl.glEnable(GL_BLEND)
            gl.glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            gl.glDepthMask(GL_FALSE)
            for stream in world_translucent:
                stream.vao.bind()
                gl.glDrawArrays(GL_TRIANGLES, 0, stream.count)
            gl.glDepthMask(GL_TRUE)
            gl.glDisable(GL_BLEND)
            gl.glDisable(GL_CULL_FACE)
        translucent = []
        if self.ghost.count:
            translucent.append(self.ghost)
        if self.volume.count:
            translucent.append(self.volume)
        if translucent:
            gl.glEnable(GL_BLEND)
            gl.glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            gl.glDepthMask(GL_FALSE)
            for stream in translucent:
                stream.vao.bind()
                gl.glDrawArrays(GL_TRIANGLES, 0, stream.count)
            gl.glDepthMask(GL_TRUE)
            gl.glDisable(GL_BLEND)
        program.setUniformValue1f(fog_amount, 0.0)  # overlays are never fogged
        if self.overlay.count:
            self.overlay.vao.bind()
            gl.glDrawArrays(GL_TRIANGLES, 0, self.overlay.count)  # visible parts
            gl.glDisable(GL_DEPTH_TEST)
            gl.glEnable(GL_BLEND)
            gl.glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            self.program.setUniformValue1f(alpha, HIDDEN_OVERLAY_ALPHA)
            gl.glDrawArrays(GL_TRIANGLES, 0, self.overlay.count)  # hidden parts, dimmed
            self.program.setUniformValue1f(alpha, 1.0)
            gl.glDisable(GL_BLEND)
            gl.glEnable(GL_DEPTH_TEST)
        if self.top_lines.count:
            gl.glDisable(GL_DEPTH_TEST)
            self.top_lines.vao.bind()
            gl.glDrawArrays(GL_LINES, 0, self.top_lines.count)
            gl.glEnable(GL_DEPTH_TEST)
        self.lines.vao.release()
