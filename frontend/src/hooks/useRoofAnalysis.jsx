import { createContext, useContext, useState, useCallback, useRef } from 'react'
import axios from 'axios'
import { geocodeAddress, reverseGeocode } from '../utils/geoUtils'

const RoofContext = createContext(null)

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function RoofProvider({ children }) {
  const [address, setAddress]         = useState('')
  const [coords, setCoords]           = useState(null)     // { lat, lng }
  const [capturedBlob, setCapturedBlob] = useState(null)   // map snapshot blob
  const [previewUrl, setPreviewUrl]   = useState(null)     // object URL for preview
  const [results, setResults]         = useState(null)     // backend analysis result
  const [isGeocoding, setIsGeocoding] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [loadingMsg, setLoadingMsg]   = useState('')
  const [error, setError]             = useState(null)
  const mapRef = useRef(null)          // Leaflet map instance ref

  // ── Geocode address ─────────────────────────────────────────────────────────
  const handleGeocode = useCallback(async (inputAddress) => {
    if (!inputAddress.trim()) { setError('Please enter an address.'); return }
    setIsGeocoding(true)
    setError(null)
    setResults(null)
    try {
      const { lat, lng, displayName } = await geocodeAddress(inputAddress)
      setCoords({ lat, lng })
      setAddress(displayName)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsGeocoding(false)
    }
  }, [])

  // ── Handle map click → update coords ───────────────────────────────────────
  const handleMapClick = useCallback(async (lat, lng) => {
    setCoords({ lat, lng })
    setResults(null)
    const name = await reverseGeocode(lat, lng)
    if (name) setAddress(name)
  }, [])

  // ── Capture map snapshot + send to backend ──────────────────────────────────
  const analyzeRoof = useCallback(async (snapshotBlob, snapshotUrl) => {
    if (!snapshotBlob || !coords) {
      setError('Please capture a map snapshot first.')
      return
    }
    setIsAnalyzing(true)
    setError(null)
    setCapturedBlob(snapshotBlob)
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    setPreviewUrl(snapshotUrl)

    try {
      setLoadingMsg('Detecting roof boundaries...')
      const formData = new FormData()
      formData.append('image', snapshotBlob, 'roof_snapshot.jpg')
      formData.append('lat', String(coords.lat))
      formData.append('lng', String(coords.lng))
      formData.append('zoom', '19')

      setLoadingMsg('Analyzing shadows & orientation...')
      const response = await axios.post(`${API_BASE}/analyze`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000,
      })

      setResults(response.data)
    } catch (err) {
      if (err.code === 'ECONNABORTED') {
        setError('Analysis timed out. The server may be busy — please try again.')
      } else if (err.response) {
        const msg = err.response.data?.detail || err.response.data?.message || 'Server error. Please try again.'
        setError(msg)
      } else if (err.request) {
        setError('Cannot reach the backend server. Make sure it is running on port 8000.')
      } else {
        setError('An unexpected error occurred. Please try again.')
      }
    } finally {
      setIsAnalyzing(false)
      setLoadingMsg('')
    }
  }, [coords, previewUrl])

  const reset = useCallback(() => {
    setAddress('')
    setCoords(null)
    setCapturedBlob(null)
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    setPreviewUrl(null)
    setResults(null)
    setError(null)
    setIsGeocoding(false)
    setIsAnalyzing(false)
    setLoadingMsg('')
  }, [previewUrl])

  return (
    <RoofContext.Provider value={{
      address, setAddress,
      coords,
      capturedBlob,
      previewUrl,
      results,
      isGeocoding,
      isAnalyzing,
      loadingMsg,
      error, setError,
      mapRef,
      handleGeocode,
      handleMapClick,
      analyzeRoof,
      reset,
    }}>
      {children}
    </RoofContext.Provider>
  )
}

export function useRoofAnalysis() {
  const ctx = useContext(RoofContext)
  if (!ctx) throw new Error('useRoofAnalysis must be used within RoofProvider')
  return ctx
}
