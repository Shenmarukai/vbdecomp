#pragma once

#include <d3dx8math.h>

//412AD0: 64-byte matrix value; original type name and provider remain unresolved.
struct Gfx_Matrix4x4
{
	Gfx_Matrix4x4();
	D3DXMATRIX matrix;
};

typedef char GfxMatrix4x4Size[(sizeof(Gfx_Matrix4x4) == 64) ? 1 : -1];
