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
 * Navigation Without Bookmarks allows the user to click anchor links (e.g., <a href="#foo">)
 * to jump to that portion of the web page without adding the anchor to the end of the
 * URL.
 */ 
const navigationWithoutBookmarksBootstrap = () => {

const navigate = event => {
    const href = event.target.getAttribute('href')
    if (href.startsWith('#')) {
        event.preventDefault()
        const destination = document.getElementById(href.substring(1))
        
        // we push state so the browser back button will return to the previous
        // scroll position
        history.pushState('', null)
        
        // and then we navigate without pushing the anchor onto the url, so the user
        // can reload the page without then autoscrolling to to this item
        destination.scrollIntoView()
        return true
    }
}

const wireUpNavigationLinks = () => {
    const containers = document.getElementsByClassName('navigation-without-bookmarks')
    for (container of containers) {
        const links = Array.from(container.getElementsByTagName('a'))
        for (link of links.filter(l => (l.getAttribute('href') || '').startsWith('#'))) {
            link.addEventListener('click', navigate)
        }
    }
}

window.addEventListener('load', wireUpNavigationLinks)

}

navigationWithoutBookmarksBootstrap()
