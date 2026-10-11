"""OpenGL drawing with PySide6's own GL wrappers (no PyOpenGL; doc/decisions.md ADR-002).

One shader draws four kinds of vertex streams: opaque triangles, translucent triangles
(drawn after, without depth writes), lines (outlines, sections) and lines drawn on top of
everything (the camera pivot). The world mesh is
split into chunks (``redsim.ui.geometry.ChunkedMesh``), each with its own buffers, so a change
re-uploads only the chunks it touched. Vertices are ``x, y, z, r, g, b, a`` float32.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtGui import QMatrix4x4, QOpenGLContext, QOpenGLFunctions
from PySide6.QtOpenGL import (
    QOpenGLBuffer,
    QOpenGLShader,
    QOpenGLShaderProgram,
    QOpenGLVertexArrayObject,
)

GL_FLOAT = 0x1406
GL_TRIANGLES = 0x0004
GL_LINES = 0x0001
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

VERTEX_SHADER = """#version 330 core
layout(location = 0) in vec3 position;
layout(location = 1) in vec4 color;
uniform mat4 mvp;
out vec4 vColor;
void main() { gl_Position = mvp * vec4(position, 1.0); vColor = color; }
"""
FRAGMENT_SHADER = """#version 330 core
in vec4 vColor;
uniform float alphaScale;
out vec4 fragColor;
void main() { fragColor = vec4(vColor.rgb, vColor.a * alphaScale); }
"""
#: Alpha of the parts of selection overlays hidden behind blocks.
HIDDEN_OVERLAY_ALPHA = 0.4
#: Alpha of building blocks in X-ray mode.
XRAY_ALPHA = 0.18


class _Stream:
    def __init__(self) -> None:
        self.vao = QOpenGLVertexArrayObject()
        self.vao.create()
        self.vbo = QOpenGLBuffer(QOpenGLBuffer.Type.VertexBuffer)
        self.vbo.create()
        self.count = 0

    def upload(self, program: QOpenGLShaderProgram, data: np.ndarray) -> None:
        data = np.ascontiguousarray(data, dtype=np.float32)
        self.count = len(data)
        self.vao.bind()
        self.vbo.bind()
        self.vbo.allocate(data.tobytes(), data.nbytes)
        program.enableAttributeArray(0)
        program.setAttributeBuffer(0, GL_FLOAT, 0, 3, 28)
        program.enableAttributeArray(1)
        program.setAttributeBuffer(1, GL_FLOAT, 12, 4, 28)
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
        #: Chunk key → (opaque, translucent, solid) streams.
        self.chunks: dict[object, tuple[_Stream, _Stream, _Stream]] = {}
        self.lines = _Stream()
        self.top_lines = _Stream()
        self.ghost = _Stream()  # translucent preview of a moved or pasted selection
        #: Selection box edges and handles (triangles): drawn normally, then again on top
        #: of everything at reduced alpha so hidden parts stay visible ("x-ray").
        self.overlay = _Stream()

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

    def upload_overlay(self, triangles: np.ndarray) -> None:
        self.program.bind()
        self.overlay.upload(self.program, triangles)

    def draw(
        self,
        mvp: np.ndarray,
        width: int,
        height: int,
        background: tuple[float, ...],
        xray: bool = False,
    ) -> None:
        """Draw everything. ``xray``: full building blocks become see-through (alpha
        ``XRAY_ALPHA``, no depth writes) while components stay opaque (Blender's X-ray)."""
        gl = self.gl
        # A QPainter overlay drawn after us may leave any of these changed.
        gl.glDisable(GL_SCISSOR_TEST)
        gl.glDisable(GL_STENCIL_TEST)
        gl.glDisable(GL_CULL_FACE)
        gl.glDisable(GL_BLEND)
        gl.glDepthMask(GL_TRUE)
        gl.glViewport(0, 0, width, height)
        gl.glClearColor(*background)
        gl.glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        gl.glEnable(GL_DEPTH_TEST)
        self.program.bind()
        location = self.program.uniformLocation("mvp")
        self.program.setUniformValue(location, QMatrix4x4(*mvp.astype(np.float32).flatten()))
        alpha = self.program.uniformLocation("alphaScale")
        self.program.setUniformValue1f(alpha, 1.0)
        for opaque, _, solid in self.chunks.values():
            for stream in (opaque,) if xray else (opaque, solid):
                if stream.count:
                    stream.vao.bind()
                    gl.glDrawArrays(GL_TRIANGLES, 0, stream.count)
        if self.lines.count:
            self.lines.vao.bind()
            gl.glDrawArrays(GL_LINES, 0, self.lines.count)
        if xray:
            gl.glEnable(GL_BLEND)
            gl.glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            gl.glDepthMask(GL_FALSE)
            self.program.setUniformValue1f(alpha, XRAY_ALPHA)
            for _, _, solid in self.chunks.values():
                if solid.count:
                    solid.vao.bind()
                    gl.glDrawArrays(GL_TRIANGLES, 0, solid.count)
            self.program.setUniformValue1f(alpha, 1.0)
            gl.glDepthMask(GL_TRUE)
            gl.glDisable(GL_BLEND)
        translucent = [stream for _, stream, _ in self.chunks.values() if stream.count]
        if self.ghost.count:
            translucent.append(self.ghost)
        if translucent:
            gl.glEnable(GL_BLEND)
            gl.glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            gl.glDepthMask(GL_FALSE)
            for stream in translucent:
                stream.vao.bind()
                gl.glDrawArrays(GL_TRIANGLES, 0, stream.count)
            gl.glDepthMask(GL_TRUE)
            gl.glDisable(GL_BLEND)
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
