/**
* Copyright (c) 2026-present, Mike West
* 
* Permission is hereby granted, free of charge, to any person obtaining a copy
* of this software and associated documentation files (the "Software"), to deal
* in the Software without restriction, including without limitation the rights
* to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
* copies of the Software, and to permit persons to whom the Software is
* furnished to do so, subject to the following conditions:
* 
* The above copyright notice and this permission notice shall be included in all
* copies or substantial portions of the Software.
* 
* THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
* IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
* FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
* AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
* LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
* OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
* SOFTWARE.
* 
*/

/** (version 0.2.0)
 * Stored Checkbox State preserves checkbox state between webpage reloads.
 *
 * If you decorate a container with `class="stored-checkbox-state"` then any checkboxes
 * within it will have their state preserved in local storage between launches.
 */
 
const storedCheckboxStateBootstrap = () => {

const onChange = event => {
    const id = event.target.id
    if (!id) return
    window.localStorage.setItem('cached-' + id, event.target.checked)
}

const wireUpElements = () => {
    const containers = document.getElementsByClassName('stored-checkbox-state')
    for (container of containers) {
        const inputs = Array.from(container.getElementsByTagName('input'))
        const checkboxes = inputs.filter(e => e.getAttribute('type') == 'checkbox' && !!e.getAttribute('id'))
        for (input of checkboxes) {
            input.addEventListener('change', onChange)
            const id = input.getAttribute('id')
            const state = window.localStorage.getItem('cached-' + id)
            const checked = state == 'true'
            if (state && checked != input.checked) {
                input.checked = checked
                const event = new Event('change')
                event.target = input
                input.dispatchEvent(event)
            }
        }
    }
}

window.addEventListener('load', wireUpElements)

}

storedCheckboxStateBootstrap()
